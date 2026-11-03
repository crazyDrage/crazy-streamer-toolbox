#!/bin/sh
# The test window on Linux: the checklist of what has to be tested (docs/tested), in a browser tab of its own,
# and next to it the test toolbox (see test-toolbox.sh): a second toolbox on temp/test_settings, port 8855,
# the same toolbox as start.sh. One stops, both stop (Ctrl+C, the terminal closed, the toolbox's window
# closed).
# The test window stays open while the toolbox is restarted. A tick is written into docs/tested at once.
# Another port for the test window:  ./test-window.sh 8860
cd "$(dirname "$0")/../.." || exit 1

# a downloaded build brings its own Python (python/); a copy of the code has a .venv
PY="python/bin/python3"
[ -x "$PY" ] || PY=".venv/bin/python"
if [ ! -x "$PY" ]; then
    echo "No Python found in $(pwd) (neither python/ nor .venv)"
    echo "Create it first: python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt"
    exit 1
fi

SETTINGS="$(pwd)/temp/test_settings"
export PYTHONPATH="$(pwd)/src"

# the test window starts the test toolbox itself and is tied to it: one stops, both stop
"$PY" -m streamer_toolbox.devtools.tested window --toolbox "$SETTINGS" "$@"
