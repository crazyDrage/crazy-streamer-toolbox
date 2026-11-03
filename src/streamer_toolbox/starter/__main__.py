"""The starter: python -m streamer_toolbox.starter [--settings <folder>] [--port 8850] [--plugins <folder>]

A small window to start the toolbox with (his round 84): how it opens, Start, its status, backups; with a tray
icon. With "Start like this next time without asking" it starts right away into the tray."""
import argparse
import logging
import sys
from pathlib import Path

from streamer_toolbox.starter.starter_app import StarterApp
from streamer_toolbox.starter.starter_tray import StarterTray
from streamer_toolbox.starter.starter_window import StarterWindow

REPO_ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    parser = argparse.ArgumentParser(prog="streamer_toolbox.starter")
    parser.add_argument("--settings", type=Path, default=REPO_ROOT / "config",
                        help="the settings folder (its toolbox.toml, flows, tokens, ...)")
    parser.add_argument("--port", type=int, default=None, help="overrides [api] port")
    parser.add_argument("--plugins", type=Path, default=REPO_ROOT / "plugins")
    args = parser.parse_args()
    app = StarterApp(args.settings, args.plugins, REPO_ROOT, args.port,
                     [sys.executable, "-m", "streamer_toolbox.starter", *sys.argv[1:]])
    app.log_file.parent.mkdir(parents=True, exist_ok=True)  # pythonw has no console: the log file says it
    logging.basicConfig(level=logging.INFO, filename=app.log_file, encoding="utf-8",
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    window: StarterWindow | None = None
    tray = StarterTray(lambda work: window.call(work), lambda: window.show(), app.open, app.restart, app.stop,
                       lambda: window.quit())
    has_tray = tray.start()
    window = StarterWindow(app, has_tray)
    window.on_quit = tray.stop

    def stopped() -> None:  # on the launcher's thread: the toolbox ended
        if app.closed_by_window:  # its window was closed and that stops it: the starter goes too, as before
            window.call(window.quit)

    app.on_stopped = stopped
    if app.settings.start_without_asking:
        window.call(window.start)
    window.root.mainloop()


if __name__ in {"__main__", "__mp_main__"}:
    main()
