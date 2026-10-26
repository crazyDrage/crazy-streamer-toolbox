"""Builds the downloads into build/:

    $env:PYTHONPATH = "src"; .venv\\Scripts\\python.exe -m streamer_toolbox.devtools.package
        build/streamer-toolbox.zip, the archive to send people (see Packager): everything is in it, and
        Settings → What you see (which starts on Normal with Works ticked) decides what of it is shown
    ... -m streamer_toolbox.devtools.package windows        (or: linux)
        build/crazy-streamer-toolbox-windows.zip / -linux.tar.gz, a download for that system only: what GitHub
        builds (.github/workflows/ci.yml); the Windows one can be built on Linux too, the Linux one only there
    $env:PYTHONPATH = "src"; .venv\\Scripts\\python.exe -m streamer_toolbox.devtools.package docs
        build/streamer-toolbox-docs.zip, the manual and the docs for AI agents (see DocBuilder)
"""
import sys
from pathlib import Path

from streamer_toolbox.devtools.package.doc_builder import DocBuilder
from streamer_toolbox.devtools.package.packager import LINUX, WINDOWS, Packager

REPO = Path(__file__).resolve().parents[4]

if __name__ == "__main__":
    if sys.argv[1:] == ["docs"]:
        DocBuilder(REPO, REPO / "build").build()
    else:
        target = next((one for one in (WINDOWS, LINUX) if one in sys.argv[1:]), "")
        Packager(REPO, REPO / "build", target=target).build()
