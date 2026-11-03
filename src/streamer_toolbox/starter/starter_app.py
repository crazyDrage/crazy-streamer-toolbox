import logging
import subprocess
import sys
import threading
import time
import tomllib
from collections.abc import Callable
from pathlib import Path

from streamer_toolbox.core.interfaces.page_opener import PageOpener
from streamer_toolbox.core.system.settings_backup import SettingsBackup
from streamer_toolbox.core.system.starter_settings import StarterSettings
from streamer_toolbox.core.system.toolbox_launcher import ToolboxLauncher
from streamer_toolbox.core.system.update_starter import UpdateStarter
from streamer_toolbox.gui.services.app_window_page_opener import LEAN_FLAGS, AppWindowPageOpener
from streamer_toolbox.gui.services.browser_page_opener import BrowserPageOpener

log = logging.getLogger(__name__)


class StarterApp:
    """What the starter window does, without the window (his round 84: a small starter with the start options,
    backups and later updates, instead of the black console window). It runs the toolbox as a child through the
    ToolboxLauncher (restart, update swap) in a thread of its own, opens it the chosen way, makes the daily
    backup of the settings folder and keeps the backups to the daily / monthly counts.

    It loads none of the toolbox's web code: that is the toolbox's own process (the old launcher took ~80 MB
    for loading it all)."""

    def __init__(self, settings: Path, plugins: Path, root: Path, port: int | None = None,
                 restart_command: list[str] | None = None,
                 make_launcher: Callable[..., ToolboxLauncher] = ToolboxLauncher) -> None:
        self.settings_folder = settings.resolve()
        self._plugins = plugins
        self._root = root
        self._port = port
        self._restart_command = restart_command or [sys.executable, "-m", "streamer_toolbox.starter"]
        self._make_launcher = make_launcher
        self.settings = StarterSettings.read(self.settings_folder)
        self.backup = SettingsBackup(self.settings_folder)
        self._launcher: ToolboxLauncher | None = None
        self._thread: threading.Thread | None = None
        self._opener: PageOpener | None = None
        self.closed_by_window = False  # the toolbox stopped because its window was closed (close_stops)
        self.on_stopped: Callable[[], None] = lambda: None

    @property
    def url(self) -> str:
        host, port = "127.0.0.1", 8850
        try:
            api = tomllib.loads((self.settings_folder / "toolbox.toml").read_text(encoding="utf-8")).get("api", {})
            host, port = str(api.get("host", host)), int(api.get("port", port))
        except (OSError, ValueError, TypeError):
            pass
        if host in ("0.0.0.0", "::"):  # listens everywhere; opened on this PC
            host = "127.0.0.1"
        return f"http://{host}:{self._port or port}"

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def save(self) -> None:
        self.settings.write(self.settings_folder)

    def start(self) -> None:
        """Daily backup (if on and none today), then the toolbox, opened the chosen way."""
        if self.running:
            return
        self.save()
        if self.settings.backup_on_start and not self.backup.made_today():
            try:
                self.back_up()
            except OSError as e:  # a backup that fails doesn't keep the toolbox from starting
                log.warning("the daily backup failed: %s", e)
        self.closed_by_window = False
        self._opener = self._opener_for(self.settings.open_mode)
        command = [sys.executable, "-m", "streamer_toolbox", "--child", "--config",
                   str(self.settings_folder / "toolbox.toml"), "--plugins", str(self._plugins)]
        command += ["--port", str(self._port)] if self._port else []
        updates = UpdateStarter(self.settings_folder / "cache" / "update", self._root, self._restart_command)
        self._launcher = self._make_launcher(command, self.url, self._opener, update=updates.start,
                                             launch=self._launch_logged)
        self._thread = threading.Thread(target=self._run, args=(self._launcher,), daemon=True)
        self._thread.start()

    @property
    def log_file(self) -> Path:
        """What the starter and the toolbox say (pythonw has no console to say it in): cache/starter.log."""
        return self.settings_folder / "cache" / "starter.log"

    def _launch_logged(self, command: list[str], stdin=None) -> subprocess.Popen:
        """The toolbox with its output into the log file (started fresh per start, the last one kept)."""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        out = self.log_file.open("a", encoding="utf-8")
        out.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} starting: {' '.join(command)}\n")
        out.flush()
        flags = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
        return subprocess.Popen(command, stdin=stdin, stdout=out, stderr=subprocess.STDOUT, **flags)

    def _run(self, launcher: ToolboxLauncher) -> None:
        try:
            code = launcher.run()
            log.info("the toolbox ended with code %s", code)
        except Exception:
            log.exception("the toolbox's launcher failed")
        finally:
            self.on_stopped()

    def stop(self) -> None:
        if self._launcher is not None:
            self._launcher.stop()

    def wait_stopped(self, seconds: float) -> None:
        """Until the toolbox has ended (after stop()), at most this long."""
        if self._thread is not None:
            self._thread.join(seconds)

    def restart(self) -> None:
        if self._launcher is not None and self.running:
            self._launcher.restart()

    def open(self) -> None:
        """Opens the toolbox again (its window was closed, or it runs without one): the chosen way, a browser tab
        when that is No window."""
        opener = self._opener if self.settings.open_mode != "none" and self._opener else BrowserPageOpener()
        opener.open(self.url)

    def back_up(self) -> Path:
        made = self.backup.make()
        self.backup.prune(self.settings.policy)
        return made

    def _opener_for(self, mode: str) -> PageOpener | None:
        if mode == "browser":
            return BrowserPageOpener()
        if mode in ("window", "lean-window"):
            from streamer_toolbox.gui.services.tied_launch import TiedLaunch
            return AppWindowPageOpener(BrowserPageOpener(), launch=TiedLaunch(),
                                       profile_dir=self.settings_folder / "app_window",
                                       on_closed=self._window_closed,
                                       flags=LEAN_FLAGS if mode == "lean-window" else ())
        return None

    def _window_closed(self) -> None:
        if self.settings.close_stops and self.running:
            self.closed_by_window = True
            self.stop()
