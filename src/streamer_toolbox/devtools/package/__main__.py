"""Builds the downloads into build/:

    $env:PYTHONPATH = "src"; .venv\\Scripts\\python.exe -m streamer_toolbox.devtools.package
        build/streamer-toolbox.zip, the archive to send people (see Packager): only what is tested is on
    ... -m streamer_toolbox.devtools.package everything
        the same archive with every box, connection, tool and trigger on (for trying, not for sending)
    $env:PYTHONPATH = "src"; .venv\\Scripts\\python.exe -m streamer_toolbox.devtools.package docs
        build/streamer-toolbox-docs.zip, the manual and the docs for AI agents (see DocBuilder)
"""
import sys
from pathlib import Path

from streamer_toolbox.devtools.package.doc_builder import DocBuilder
from streamer_toolbox.devtools.package.packager import Packager

REPO = Path(__file__).resolve().parents[4]

if __name__ == "__main__":
    if sys.argv[1:] == ["docs"]:
        DocBuilder(REPO, REPO / "build").build()
    else:
        Packager(REPO, REPO / "build", tested_only=sys.argv[1:] != ["everything"]).build()
