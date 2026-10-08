import shutil
import subprocess
import threading
from pathlib import Path
from typing import Callable, Sequence

from streamer_toolbox.core.interfaces.page_opener import PageOpener

# Chromium browsers can show a page as an app: own window and taskbar entry, no tabs or address bar.
DEFAULT_BROWSERS = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
)
# on Linux (and anywhere else) they are found by their command's name
BROWSER_COMMANDS = ("microsoft-edge", "microsoft-edge-stable", "google-chrome", "google-chrome-stable",
                    "chromium", "chromium-browser", "brave-browser")


def installed_browsers(which: Callable[[str], str | None] = shutil.which) -> tuple[Path, ...]:
    """Where to look for a Chromium browser: Windows' usual folders, then the commands on the PATH."""
    found = (which(command) for command in BROWSER_COMMANDS)
    return DEFAULT_BROWSERS + tuple(Path(path) for path in found if path)


class AppWindowPageOpener(PageOpener):
    """Opens the dashboard in its own app window via Edge, Chrome or another Chromium browser (Windows and
    Linux); falls back when none is installed.

    With a profile folder the window gets a browser process of its own (not handed to an Edge that's already
    open), so the process ends when the window is closed and on_closed runs: the X closes the toolbox."""

    def __init__(self, fallback: PageOpener, browsers: Sequence[Path] | None = None,
                 launch: Callable[[list[str]], object] = subprocess.Popen,
                 window_size: tuple[int, int] = (1280, 800), profile_dir: Path | None = None,
                 on_closed: Callable[[], None] | None = None) -> None:
        self._fallback = fallback
        self._browsers = installed_browsers() if browsers is None else browsers
        self._launch = launch
        self._window_size = window_size
        self._profile_dir = profile_dir
        self._on_closed = on_closed

    def open(self, url: str) -> None:
        browser = next((b for b in self._browsers if b.exists()), None)
        if browser is None:
            self._fallback.open(url)
            return
        width, height = self._window_size
        command = [str(browser), f"--app={url}", f"--window-size={width},{height}"]
        if self._profile_dir is not None:
            command += [f"--user-data-dir={self._profile_dir}", "--no-first-run", "--no-default-browser-check"]
        process = self._launch(command)
        if self._profile_dir is not None and self._on_closed is not None and hasattr(process, "wait"):
            threading.Thread(target=self._wait_then_close, args=(process,), daemon=True).start()

    def _wait_then_close(self, process) -> None:
        process.wait()
        self._on_closed()
