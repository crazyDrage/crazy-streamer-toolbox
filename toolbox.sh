#!/bin/sh
# The running toolbox from a terminal: it calls the toolbox's API.
#   ./toolbox.sh list        ./toolbox.sh list 'obs.*'        ./toolbox.sh info hello.greet
#   ./toolbox.sh run hello.greet name=chat
# The toolbox itself has to be running (start.sh). More: ./toolbox.sh --help
here="$(cd "$(dirname "$0")" && pwd)"
PYTHONPATH="$here/src" exec "$here/.venv/bin/python" -m streamer_toolbox.cli "$@"
