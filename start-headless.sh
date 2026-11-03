#!/bin/sh
# Start streamer-toolbox without any window (headless): open it in any browser or on your phone, at
# http://127.0.0.1:8850 (or the port you set). Ctrl+C stops it.
echo "The toolbox runs without a window: open http://127.0.0.1:8850 (or your own port) in any browser."
exec "$(dirname "$0")/start.sh" --open none "$@"
