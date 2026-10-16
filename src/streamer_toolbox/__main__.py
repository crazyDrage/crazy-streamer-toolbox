"""Start the toolbox: python -m streamer_toolbox [--config config/toolbox.toml | --settings <folder>] [--port 8850]
[--plugins <folder>] [--open none|browser|window]

Everything the toolbox keeps (flows, variables, tokens, ...) is in the folder of its settings file, so
--settings <folder> starts it on a whole other set, e.g. the test settings (docs/tested/test-toolbox.bat).

This process is the launcher: it opens the page and runs the toolbox itself as a child (--child), which it starts
again when the toolbox asks for a restart (Settings → Restart)."""
import argparse
import logging
import secrets
import sys
from pathlib import Path

from nicegui import app, ui

from streamer_toolbox.assembly.toolbox_assembly import assemble
from streamer_toolbox.core.app_name import APP_NAME
from streamer_toolbox.core.config.toolbox_config import ToolboxConfig
from streamer_toolbox.core.system.parent_watch import ParentWatch
from streamer_toolbox.core.system.toolbox_launcher import ToolboxLauncher
from streamer_toolbox.gui.services.app_window_page_opener import AppWindowPageOpener
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
    parser.add_argument("--open", choices=("none", "browser", "window"), default="none",
                        help="show the dashboard once running: browser tab or app window (Edge/Chrome)")
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)  # run by the launcher
    args = parser.parse_args()
    if args.settings is not None:
        args.config = args.settings / "toolbox.toml"
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    config = ToolboxConfig.read(args.config)
    if not args.child:
        sys.exit(_launch(args, config))
    log.info("config: %s", args.config if args.config.exists() else "none found, using defaults")
    _, restart = assemble(args, config)
    ParentWatch(sys.stdin.fileno(), app.shutdown).start()  # the launcher closes our stdin: window closed, Ctrl+C
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
        if args.open == "window":
            # closing the window stops the toolbox (his wish, round 12); a restart keeps the window
            opener = AppWindowPageOpener(opener, profile_dir=args.config.parent / "app_window",
                                         on_closed=lambda: launcher.stop())
    launcher = ToolboxLauncher(command, f"http://{host}:{args.port or config.port}", opener)
    return launcher.run()


def _session_secret(path: Path) -> str:
    """Signs the cookie that keeps another device signed in; made once, kept in config/ (not in git).
    Not in config/secrets/: with a login set those files are encrypted, and the server needs this one to
    show the login page at all."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(secrets.token_urlsafe(32), encoding="utf-8")
    return path.read_text(encoding="utf-8").strip()


if __name__ in {"__main__", "__mp_main__"}:
    main()
