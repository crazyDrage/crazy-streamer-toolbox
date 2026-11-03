#!/bin/sh
# start-settings: a small window to start the toolbox with (how it opens, its status, Open / Restart / Stop,
# backups of the settings), with a tray icon when the desktop has a tray. Needs tkinter (python3-tk).
cd "$(dirname "$0")" || exit 1
PYTHONPATH="$(pwd)/src" exec .venv/bin/python -m streamer_toolbox.starter "$@"
