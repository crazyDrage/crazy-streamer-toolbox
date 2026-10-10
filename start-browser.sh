#!/bin/sh
# Start streamer-toolbox on Linux and open the dashboard as a tab in the default browser.
exec "$(dirname "$0")/start.sh" --open browser "$@"
