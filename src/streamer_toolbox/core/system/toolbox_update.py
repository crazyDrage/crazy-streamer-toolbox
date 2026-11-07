import asyncio
import hashlib
import json
import logging
import shutil
import sys
import tarfile
import time
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from streamer_toolbox.core.app_version import APP_VERSION, channel_takes, is_newer, version_numbers
from streamer_toolbox.core.files.write_whole import write_whole
from streamer_toolbox.core.system.settings_backup import SettingsBackup
from streamer_toolbox.core.system.starter_settings import StarterSettings
from streamer_toolbox.core.system.toolbox_release import ToolboxRelease
from streamer_toolbox.core.system.update_files import READY, RESULT
from streamer_toolbox.core.web.web_client import web_client
from streamer_toolbox.core.web.web_error import web_error

log = logging.getLogger(__name__)
REPO = "crazyDrage/crazy-streamer-toolbox"
API = "https://api.github.com/repos/{repo}/releases/latest"  # GitHub's "latest" is never a pre-release
ALL = "https://api.github.com/repos/{repo}/releases?per_page=30"  # with the test versions, newest first
# which versions are offered (his answer of 2026-11-01: "Default is using the normal version, we can change it
# to the other versions if needed"; test versions "only if we enable the settings. Never in default"): each
# takes that stage and every later one, so "beta" also gets rc's and releases
CHANNELS = {"release": "Releases only", "rc": "Release candidates too", "beta": "Betas too",
            "alpha": "Alphas too", "dev": "Everything (also dev versions)"}
# the release's download per system (the public repo's ci.yml builds them under these names)
ASSETS = {"windows": "crazy-streamer-toolbox-windows.zip", "linux": "crazy-streamer-toolbox-linux.tar.gz"}
CHECKED = "checked.json"  # the last check: when, and the newest release then
DAY = 24 * 60 * 60


class ToolboxUpdate:
    """The toolbox's own update (his next release plan, part 1: "both", tell and download and install, shown
    at the top). check() asks GitHub for the newest release at most once a day; a newer one than APP_VERSION is
    `newest`. prepare() downloads its file for this system into `folder`, checks it against the SHA-256 GitHub
    lists, unpacks it and writes ready.json; the toolbox then stops with UPDATE_EXIT_CODE and its launcher
    starts the swap (UpdateStarter → UpdateSwap), which puts the new files in and starts it again.

    Only a toolbox from a download can install (`installable`: it has its own python folder and no .git); one
    run from the code (like on his PC) only tells. Nothing of the settings folder is ever replaced, and before
    the toolbox stops for an update the settings folder is copied into backups/ (his answer: "make sure that
    we have a backup of the settings before we update").

    `channel` (CHANNELS): which versions count; "release" (the default) never offers a test version."""

    def __init__(self, root: Path, folder: Path, transport: httpx.AsyncBaseTransport | None = None,
                 now: Callable[[], float] = time.time, check_every: float = DAY, system: str = "",
                 version: str = APP_VERSION, settings: Path | None = None, channel: str = "release") -> None:
        self._root = root
        self._folder = folder
        self._settings = settings
        self.channel = channel if channel in CHANNELS else "release"
        self._transport = transport
        self._now = now
        self._check_every = check_every
        self._system = system or ("windows" if sys.platform == "win32" else "linux")
        self._version = version
        self._busy = asyncio.Lock()

    @property
    def installable(self) -> bool:
        return (self._root / "python").is_dir() and not (self._root / ".git").exists()

    @property
    def newest(self) -> ToolboxRelease | None:
        """The newer release the last check found, None if there is none (or no check yet)."""
        saved = self._read(CHECKED).get("release")
        try:
            release = ToolboxRelease(**saved) if isinstance(saved, dict) else None
        except TypeError:
            return None
        if release is None or not self._wanted(release.version):
            return None
        return release if is_newer(release.version, self._version) else None

    def _wanted(self, version: str) -> bool:
        """A version of a stage the channel takes (a test version only when he chose it)."""
        return channel_takes(self.channel, version)

    async def check(self, force: bool = False) -> ToolboxRelease | None:
        """Asks GitHub unless it was asked less than a day ago (force: now); the newer release, or None. Fails
        with the reason when GitHub can't be asked."""
        async with self._busy:
            checked = self._read(CHECKED).get("checked")
            if not force and checked is not None and self._now() - float(checked) < self._check_every:
                return self.newest
            address = (API if self.channel == "release" else ALL).format(repo=REPO)
            async with web_client(self._transport, timeout=30, follow_redirects=True) as client:
                try:
                    answer = await client.get(address, headers={"Accept": "application/vnd.github+json"})
                    answer.raise_for_status()
                    data = answer.json()
                except (httpx.HTTPError, ValueError) as e:
                    raise RuntimeError(f"GitHub didn't answer ({web_error(e)})") from None
            if isinstance(data, list):  # every release: the newest one the channel takes
                fitting = [r for r in data if isinstance(r, dict) and not r.get("draft")
                           and self._wanted(str(r.get("tag_name", "")))]
                data = max(fitting, key=lambda r: version_numbers(str(r["tag_name"])), default={})
            release = self._release(data)
            self._write(CHECKED, {"checked": self._now(), "release": release.__dict__ if release else None})
            return self.newest

    async def prepare(self, release: ToolboxRelease) -> Path:
        """Downloads and unpacks the release; the folder with the new toolbox in it (ready.json names it)."""
        if not self.installable:
            raise RuntimeError("this toolbox runs from its code, not from a download: get the new version from "
                               f"{release.page}")
        if not release.url.startswith(f"https://github.com/{REPO}/releases/download/"):
            raise RuntimeError("the file's address is not one of the toolbox's releases: not downloaded")
        if not release.digest.startswith("sha256:"):
            raise RuntimeError(f"GitHub lists no SHA-256 for {release.asset}: not downloaded")
        async with self._busy:
            self._folder.mkdir(parents=True, exist_ok=True)
            archive = self._folder / release.asset
            sha = hashlib.sha256()
            try:
                async with web_client(self._transport, timeout=60, follow_redirects=True) as client:
                    async with client.stream("GET", release.url) as download:
                        download.raise_for_status()
                        with archive.open("wb") as out:
                            async for part in download.aiter_bytes(1 << 20):
                                sha.update(part)
                                out.write(part)
                if sha.hexdigest() != release.digest.removeprefix("sha256:").lower():
                    raise RuntimeError(f"{release.asset} is not the file GitHub lists (its SHA-256 differs): "
                                       "not used")
                new = await asyncio.to_thread(self._unpack, archive, self._folder / release.version)
            except httpx.HTTPError as e:
                raise RuntimeError(f"the download failed ({web_error(e)})") from None
            finally:
                archive.unlink(missing_ok=True)
            if self._settings is not None:  # no copy, no update: a failed copy stops it here
                await asyncio.to_thread(self.back_up, release.version)
            self._write(READY, {"version": release.version, "new": str(new)})
            return new

    def back_up(self, version: str) -> Path:
        """The settings folder as it is now, in backups/before-<version>-<date and time>.zip (SettingsBackup:
        without the downloads, the backups and the window's browser data), then the old ones beyond the starter's
        daily / monthly counts go. Unpack it over the settings folder to go back."""
        backup = SettingsBackup(self._settings, self._now)
        target = backup.make(f"before-{version}")
        backup.prune(StarterSettings.read(self._settings).policy)
        log.info("settings kept in %s before the update to %s", target, version)
        return target

    def result(self) -> dict[str, Any] | None:
        """What the last update did ({version, ok, error}), once: read at the start after it."""
        result = self._read(RESULT)
        (self._folder / RESULT).unlink(missing_ok=True)
        return result or None

    def clean(self) -> None:
        """Removes what an update left behind (the unpacked download, the old files); one still in use stays
        until the next start."""
        if not self._folder.is_dir() or (self._folder / READY).exists():
            return
        for item in self._folder.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)

    def _release(self, data: dict[str, Any]) -> ToolboxRelease | None:
        version = str(data.get("tag_name", "")).strip().removeprefix("v")
        if not self._wanted(version) or not is_newer(version, self._version):
            return None
        name = ASSETS.get(self._system, "")
        asset = next((a for a in data.get("assets") or [] if a.get("name") == name), {})
        return ToolboxRelease(version, str(data.get("body") or ""), str(data.get("html_url") or ""), name,
                              str(asset.get("browser_download_url") or ""), str(asset.get("digest") or ""))

    @staticmethod
    def _unpack(archive: Path, target: Path) -> Path:
        """The archive into target (no name in it can lead out of it); the folder in it that holds src/."""
        shutil.rmtree(target, ignore_errors=True)
        target.mkdir(parents=True)
        if archive.name.endswith(".zip"):
            with zipfile.ZipFile(archive) as packed:
                packed.extractall(target)  # zipfile drops "..", drive letters and leading slashes
        else:
            with tarfile.open(archive) as packed:
                packed.extractall(target, filter="data")
        new = next((d.parent.parent for d in sorted(target.glob("*/src/streamer_toolbox")) if d.is_dir()), None)
        if new is None:
            shutil.rmtree(target, ignore_errors=True)
            raise RuntimeError("the download has no toolbox in it")
        return new

    def _read(self, name: str) -> dict[str, Any]:
        try:
            data = json.loads((self._folder / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write(self, name: str, data: dict[str, Any]) -> None:
        self._folder.mkdir(parents=True, exist_ok=True)
        write_whole(self._folder / name, json.dumps(data, indent=1))
