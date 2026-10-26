"""Starts a program that sleeps through TiedLaunch (a minute; with `plain` through plain Popen, 6 s), then
ends at once without any clean up, as a closed console does.

    python -m tests.helpers.tied_launch_once [plain]

The sleeping program inherits this one's stdout: once both are gone, whoever reads that stdout gets its end
(TestTiedLaunch)."""
import os
import subprocess
import sys
import time

from streamer_toolbox.gui.services.tied_launch import TiedLaunch

if __name__ == "__main__":
    plain = sys.argv[1:] == ["plain"]
    launch = subprocess.Popen if plain else TiedLaunch()
    launch([sys.executable, "-c", f"import time; time.sleep({6 if plain else 60})"])
    time.sleep(0.5)  # it is running
    print("started", flush=True)
    os._exit(1)
