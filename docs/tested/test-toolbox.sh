#!/bin/sh
# The test toolbox on Linux: a second toolbox on its own settings folder (temp/test_settings) and its own port
# (8855), with a numbered flow for every box (Start + that box), so nothing has to be built
# first. The numbers are the ones the test window shows (test-window.sh). What you set in a test flow stays,
# a test flow you delete stays deleted.
# It runs next to your own toolbox and never touches its settings. Another folder:  ./test-toolbox.sh <folder>
cd "$(dirname "$0")/../.." || exit 1

# a downloaded build brings its own Python (python/); a copy of the code has a .venv
PY="python/bin/python3"
[ -x "$PY" ] || PY=".venv/bin/python"
if [ ! -x "$PY" ]; then
    echo "No Python found in $(pwd) (neither python/ nor .venv)"
    echo "Create it first: python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt"
    exit 1
fi

SETTINGS="${1:-$(pwd)/temp/test_settings}"
export PYTHONPATH="$(pwd)/src"

echo "Writing the test flows into $SETTINGS/flows ..."
"$PY" -m streamer_toolbox.devtools.tested flows "$SETTINGS" || exit 1

# its own page settings too, so the two toolboxes don't write the same file
NICEGUI_STORAGE_PATH="$SETTINGS/.nicegui" exec "$PY" -m streamer_toolbox --settings "$SETTINGS" \
    --port 8855 --open window
