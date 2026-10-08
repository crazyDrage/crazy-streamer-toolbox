#!/bin/sh
# The test window on Linux: the checklist of what has to be tested (docs/tested), in a browser tab of its own.
# Keep it open next to the toolbox; it needs no running toolbox and stays open while that is restarted.
# A tick is written into docs/tested at once. Another port:  ./test-window.sh 8860
cd "$(dirname "$0")/../.." || exit 1

if [ ! -x ".venv/bin/python" ]; then
    echo "No .venv found in $(pwd)"
    echo "Create it first: python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt"
    exit 1
fi

PYTHONPATH="$(pwd)/src" exec .venv/bin/python -m streamer_toolbox.devtools.tested window "$@"
