"""Start the toolbox: python -m streamer_toolbox [--config config/toolbox.toml | --settings <folder>] [--port 8850]
[--plugins <folder>] [--open none|browser|window|lean-window]

Everything the toolbox keeps (flows, variables, tokens, ...) is in the folder of its settings file, so
--settings <folder> starts it on a whole other set, e.g. the test settings (docs/tested/test-toolbox.bat).

This process is the launcher: it opens the page and runs the toolbox itself as a child (--child), which it starts
again when the toolbox asks for a restart (Settings → Restart)."""
import argparse
import logging
import os
import secrets
import sys
from pathlib import Path

from nicegui import app, ui

from streamer_toolbox.assembly.toolbox_assembly import assemble
from streamer_toolbox.core.app_name import APP_NAME
from streamer_toolbox.core.config.toolbox_config import ToolboxConfig
from streamer_toolbox.core.files.write_whole import write_whole
from streamer_toolbox.core.system.parent_watch import ParentWatch
from streamer_toolbox.core.system.toolbox_launcher import ToolboxLauncher
from streamer_toolbox.core.system.update_starter import UpdateStarter
from streamer_toolbox.gui.services.app_window_page_opener import LEAN_FLAGS, AppWindowPageOpener
from streamer_toolbox.gui.services.tied_launch import TiedLaunch
from streamer_toolbox.gui.services.browser_page_opener import BrowserPageOpener

REPO_ROOT = Path(__file__).resolve().parents[2]
log = logging.getLogger("streamer_toolbox")


def main() -> None:
    parser = argparse.ArgumentParser(prog="streamer_toolbox")
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "config" / "toolbox.toml")
    parser.add_argument("--settings", type=Path, default=None,
                        help="another settings folder: its toolbox.toml, and its flows, variables, tokens ... "
                             "(the same as --config <folder>/toolbox.toml)")
    parser.add_argument("--port", type=int, default=None, help="overrides [api] port")
    parser.add_argument("--plugins", type=Path, default=REPO_ROOT / "plugins")
    parser.add_argument("--open", choices=("none", "browser", "window", "lean-window"), default="none",
                        help="show the dashboard once running: browser tab, app window (Edge/Chrome) or an app "
                             "window that uses less memory (Edge's extras off; start-settings offers it)")
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)  # run by the launcher
    # started by another program (the test window, TiedToolbox): stop when it closes our stdin or is gone
    parser.add_argument("--tied", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    # pythonw (the starter) has no console: its output is missing or points nowhere, and NiceGUI's "ready to go"
    # line then stopped the start (OSError 22, 11-03). Such output goes to nothing instead
    for name in ("stdout", "stderr"):
        if not _writable(getattr(sys, name)):
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))
    if args.settings is not None:
        args.config = args.settings / "toolbox.toml"
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    # httpx writes every request's whole address at INFO: a web box's key can be in one ({secret.key})
    logging.getLogger("httpx").setLevel(logging.WARNING)
    config = ToolboxConfig.read(args.config)
    if not args.child:
        sys.exit(_launch(args, config))
    log.info("config: %s", args.config if args.config.exists() else "none found, using defaults")
    _, restart = assemble(args, config)
    # the launcher closes our stdin: window closed, Ctrl+C. Watched once the server runs: app.shutdown() before
    # that fails, and a stop while it starts was lost (the toolbox ran on with nobody to stop it)
    app.on_startup(lambda: ParentWatch(sys.stdin.fileno(), app.shutdown).start())
    ui.run(host=config.host, port=args.port or config.port, title=APP_NAME, show=False, reload=False,
           storage_secret=_session_secret(args.config.parent / "session_secret.txt"))
    sys.exit(restart.exit_code)


def _launch(args: argparse.Namespace, config: ToolboxConfig) -> int:
    """The launcher: runs the toolbox as a child, opens the page once it answers, starts it again on Restart."""
    command = [sys.executable, "-m", "streamer_toolbox", "--child", "--config", str(args.config),
               "--plugins", str(args.plugins)] + (["--port", str(args.port)] if args.port else [])
    host = "127.0.0.1" if config.host in ("0.0.0.0", "::") else config.host  # 0.0.0.0 isn't an address to open
    launcher: ToolboxLauncher | None = None
    opener = None
    if args.open != "none":
        opener = BrowserPageOpener()
        if args.open in ("window", "lean-window"):
            # closing the window stops the toolbox (his wish, round 12); a restart keeps the window, and the
            # window goes when the toolbox stops, also when its console is closed (OPEN 93)
            # a full path: with a relative one (--config temp\x\toolbox.toml) Edge finds no profile of its own and
            # hands the page to an Edge that's already open, where it didn't work ("no ES modules", 2026-11-03)
            opener = AppWindowPageOpener(opener, launch=TiedLaunch(),
                                         profile_dir=args.config.resolve().parent / "app_window",
                                         on_closed=lambda: launcher.stop(),
                                         flags=LEAN_FLAGS if args.open == "lean-window" else ())
    # an update (his next release plan, part 1): the swap starts the toolbox again the way it was started now
    restart = UpdateStarter.restart_command(REPO_ROOT, [a for a in sys.argv[1:] if a != "--tied"],
                                            args.open == "window")
    updates = UpdateStarter(args.config.parent / "cache" / "update", REPO_ROOT, restart)
    launcher = ToolboxLauncher(command, f"http://{host}:{args.port or config.port}", opener, update=updates.start)
    if args.tied:
        ParentWatch(sys.stdin.fileno(), launcher.stop).start()
    return launcher.run()


def _writable(stream) -> bool:
    """Whether output can go to this stream: it is there and its handle points somewhere."""
    if stream is None:
        return False
    try:  # pythonw's handles look like pipes but every write fails: only writing tells
        stream.write("\n")
        stream.flush()
    except (OSError, ValueError, AttributeError):
        return False
    return True


def _session_secret(path: Path) -> str:
    """Signs the cookie that keeps another device signed in; made once, kept in config/ (not in git).
    Not in config/secrets/: with a login set those files are encrypted, and the server needs this one to
    show the login page at all."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        write_whole(path, secrets.token_urlsafe(32))
    return path.read_text(encoding="utf-8").strip()


if __name__ in {"__main__", "__mp_main__"}:
    main()
