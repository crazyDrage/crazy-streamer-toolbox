"""Whether this copy of the toolbox is a build that only offers what was tested.

The packager puts the file RELEASE_MARKER next to the code of such a build. The project folder never has it:
there every box, connection, tool and trigger is on, so it can be tested (TestList; ticked in the test window, devtools/tested)."""
from pathlib import Path

RELEASE_MARKER = "tested_only.txt"
PACKAGE = Path(__file__).resolve().parents[2]  # .../streamer_toolbox


def is_release(package: Path = PACKAGE) -> bool:
    return (package / RELEASE_MARKER).is_file()
