import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

# python-build-standalone (github.com/astral-sh/python-build-standalone): Pythons that run from any folder
LATEST = "https://raw.githubusercontent.com/astral-sh/python-build-standalone/latest-release/latest-release.json"
FILE = r"cpython-{minor}\.\d+\+\d+-x86_64-unknown-linux-gnu-install_only_stripped\.tar\.gz"


class LinuxPython:
    """The Python the Linux download carries, so nothing has to be installed on that PC: a ready-made build
    that runs from any folder (python-build-standalone, 64 bit x86), unpacked into <folder>/python, with every
    library from requirements.txt installed into it.

    Only on Linux: the libraries are installed by that Python itself, and one of them (evdev, for the keyboard
    triggers) is compiled while doing so, which needs a C compiler on the PC that builds. The download then
    needs neither. It runs on a Linux at least as new as the one it was built on (its C library).
    The downloaded archive is kept in `cache` and checked against the project's own list of checksums."""

    def __init__(self, cache: Path, minor: str = "") -> None:
        self._cache = cache
        self._minor = minor or "{}.{}".format(*sys.version_info[:2])

    def put(self, folder: Path, requirements: Path) -> str:
        """Unpacks the Python into <folder>/python and installs the libraries; gives its version."""
        if sys.platform != "linux":
            raise RuntimeError("The Linux download is built on Linux (GitHub does it: .github/workflows/ci.yml): "
                               "its Python has to install the libraries itself")
        archive = self._download()
        with tarfile.open(archive) as packed:
            packed.extractall(folder, filter="data")  # everything in it is below python/
        python = folder / "python" / "bin" / "python3"
        subprocess.run([str(python), "-m", "pip", "install", "--quiet", "--no-compile", "--no-warn-script-location",
                        "-r", str(requirements)], check=True,
                       env={**os.environ, "CC": os.environ.get("CC", "gcc")})  # that Python names clang as its own
        return archive.name.split("-")[1].split("+")[0]

    def _download(self) -> Path:
        prefix = json.loads(_read(LATEST))["asset_url_prefix"]
        sums = _read(f"{prefix}/SHA256SUMS").decode()
        found = re.search(r"^(\w{64})\s+\*?(" + FILE.format(minor=re.escape(self._minor)) + r")$", sums, re.M)
        if found is None:
            raise LookupError(f"python-build-standalone's newest release has no Python {self._minor} for Linux")
        checksum, name = found.groups()
        archive = self._cache / name
        if not archive.is_file():
            archive.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(f"{prefix}/{name.replace('+', '%2B')}", archive)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != checksum:
            archive.unlink()
            raise ValueError(f"{name} does not have the checksum its release lists; it was removed, try again")
        return archive


def _read(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as answer:
        return answer.read()
