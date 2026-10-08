#!/bin/sh
# Start streamer-toolbox (GUI + HTTP API) on Linux and open the dashboard in its own window (a Chromium
# browser's app window; without one it opens as a browser tab). start-browser.sh opens a tab instead.
# Extra options are passed on, e.g.  ./start.sh --port 8851 --config config/other.toml   or   ./start.sh --open none
# Closing the dashboard window stops the toolbox. Settings -> Restart starts it again; the window stays open.
cd "$(dirname "$0")" || exit 1

if [ ! -x ".venv/bin/python" ]; then
    echo "No .venv found in $(pwd)"
    echo "Create it first: python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt"
    exit 1
fi

PYTHONPATH="$(pwd)/src" exec .venv/bin/python -m streamer_toolbox --open window "$@"
