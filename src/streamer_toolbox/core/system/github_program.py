import asyncio
import hashlib
import json
import logging
import os
import shutil
import time
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from streamer_toolbox.core.web.web_client import web_client

log = logging.getLogger(__name__)
API = "https://api.github.com/repos/{repo}/releases/latest"
STATE = "installed.json"
DAY = 24 * 60 * 60


class GithubProgram:
    """A program the toolbox doesn't bring along but gets from a GitHub project's releases, and keeps up to date:
    the newest release's zip for this system, unpacked into its own folder inside the settings folder.

    path() gives the program's file. The first time it downloads it; after that it asks GitHub at most once
    a day whether there is a newer release and takes it. A check that fails (no internet, GitHub's limit of 60
    asks an hour) never stops a program that is there already.

    What is downloaded is checked before it is used: the file must come from that project's own release
    address, and its SHA-256 must be the one GitHub lists for it. Each version is unpacked into a folder of
    its own (a running program can't be overwritten on Windows); older ones are removed when they are free.
    `asset` says which of the release's files is the one for this system (by its name)."""

    def __init__(self, repo: str, asset: Callable[[str], bool], program: str, folder: Path,
                 transport: httpx.AsyncBaseTransport | None = None, now: Callable[[], float] = time.time,
                 check_every: float = DAY) -> None:
        self._repo = repo
        self._asset = asset
        self._program = program
        self._folder = folder
        self._transport = transport
        self._now = now
        self._check_every = check_every
        self._busy = asyncio.Lock()

    @property
    def version(self) -> str:
        """The version that is installed, "" if none."""
        return str(self._state().get("version", "")) if self._file() else ""

    async def path(self) -> Path:
        """The program's file, downloaded first if it is not there, updated if a day has passed and there is
        a newer one."""
        async with self._busy:
            if self._file() is None:
                await self._take_newest()
            elif self._now() - float(self._state().get("checked", 0)) >= self._check_every:
                try:
                    await self._take_newest()
                except Exception as e:  # the one that is there keeps working
                    log.warning("%s: update check failed (%s); keeping %s", self._repo, e, self.version)
                    self._write({**self._state(), "checked": self._now()})
            file = self._file()
            if file is None:
                raise RuntimeError(f"{self._program} is not there after the download")
            return file

    async def update(self) -> dict[str, Any]:
        """Asks GitHub now; gives {version, updated}. Fails with the reason if GitHub can't be asked."""
        async with self._busy:
            before = self.version
            await self._take_newest()
            return {"version": self.version, "updated": self.version != before}

    def _file(self) -> Path | None:
        version = str(self._state().get("version", ""))
        file = self._folder / version / self._program if version else None
        return file if file is not None and file.is_file() else None

    def _state(self) -> dict[str, Any]:
        try:
            return json.loads((self._folder / STATE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _write(self, state: dict[str, Any]) -> None:
        self._folder.mkdir(parents=True, exist_ok=True)
        (self._folder / STATE).write_text(json.dumps(state, indent=1), encoding="utf-8")

    async def _take_newest(self) -> None:
        """Installs the newest release unless it is the one that is there; notes the time of the check."""
        async with web_client(self._transport, timeout=30, follow_redirects=True) as client:
            try:
                answer = await client.get(API.format(repo=self._repo),
                                          headers={"Accept": "application/vnd.github+json"})
                answer.raise_for_status()
                release = answer.json()
            except (httpx.HTTPError, ValueError) as e:
                raise RuntimeError(f"GitHub didn't answer for {self._repo} ({e or type(e).__name__})") from None
            version = str(release.get("tag_name", "")).strip()
            if not version or any(sign in version for sign in "/\\") or version.startswith("."):
                raise RuntimeError(f"GitHub names no usable version for {self._repo}: {version!r}")
            if version != self.version or self._file() is None:
                asset = next((a for a in release.get("assets") or [] if self._asset(str(a.get("name", "")))), None)
                if asset is None:
                    raise RuntimeError(f"release {version} of {self._repo} has no file for this system")
                await self._install(client, version, asset)
                log.info("%s: %s installed in %s", self._repo, version, self._folder / version)
        self._write({"version": version, "checked": self._now(), "repo": self._repo})
        self._remove_others(version)

    async def _install(self, client: httpx.AsyncClient, version: str, asset: dict[str, Any]) -> None:
        url, digest = str(asset.get("browser_download_url", "")), str(asset.get("digest") or "")
        if not url.startswith(f"https://github.com/{self._repo}/releases/download/"):
            raise RuntimeError(f"the file's address is not a release of {self._repo}: not downloaded")
        if not digest.startswith("sha256:"):
            raise RuntimeError(f"GitHub lists no SHA-256 for {asset.get('name')}: not downloaded")
        self._folder.mkdir(parents=True, exist_ok=True)
        archive = self._folder / "download.zip"
        sha = hashlib.sha256()
        try:
            async with client.stream("GET", url) as download:
                download.raise_for_status()
                with archive.open("wb") as out:
                    async for part in download.aiter_bytes(1 << 20):
                        sha.update(part)
                        out.write(part)
            if sha.hexdigest() != digest.removeprefix("sha256:").lower():
                raise RuntimeError(f"{asset.get('name')} is not the file GitHub lists (its SHA-256 differs): "
                                   "not used")
            await asyncio.to_thread(self._unpack, archive, self._folder / version)
        except httpx.HTTPError as e:
            raise RuntimeError(f"the download of {asset.get('name')} failed ({e or type(e).__name__})") from None
        finally:
            archive.unlink(missing_ok=True)

    def _unpack(self, archive: Path, target: Path) -> None:
        """The zip's files into the folder, flat: a name in the zip can't lead out of it."""
        shutil.rmtree(target, ignore_errors=True)
        target.mkdir(parents=True)
        with zipfile.ZipFile(archive) as packed:
            for member in packed.infolist():
                name = Path(member.filename.replace("\\", "/")).name
                if member.is_dir() or not name:
                    continue
                with packed.open(member) as source, (target / name).open("wb") as out:
                    shutil.copyfileobj(source, out)
        program = target / self._program
        if not program.is_file():
            shutil.rmtree(target, ignore_errors=True)
            raise RuntimeError(f"the download has no {self._program} in it")
        if os.name != "nt":
            program.chmod(0o755)

    def _remove_others(self, version: str) -> None:
        for other in self._folder.iterdir():
            if other.is_dir() and other.name != version:
                shutil.rmtree(other, ignore_errors=True)  # one that is still running stays until next time
