import asyncio
import hashlib
import shutil
import zipfile
from pathlib import Path

import httpx

from streamer_toolbox.core.app_version import version_numbers
from streamer_toolbox.core.web.web_client import web_client
from streamer_toolbox.core.web.web_error import web_error
from streamer_toolbox.plugins.listed_plugin import ListedPlugin
from streamer_toolbox.plugins.plugin_manifest import MANIFEST, PluginManifest

LARGEST = 50 * 1024 * 1024  # a plugin's download; more is not a plugin
LARGEST_UNPACKED = 200 * 1024 * 1024  # unpacked (a small zip can unpack to terabytes: a "zip bomb")
MOST_FILES = 10000


class PluginInstaller:
    """Downloads a listed plugin and puts it into the plugins folder (his answer of 2026-11-01: "the tool can
    download and import the plugin itself"). The download is a zip with the plugin folder in it (plugin.json
    at its top or one folder down, as GitHub's own zips have it); its plugin.json must have the listed id and
    version. A plugin that is there already (an update, or going back to an older version) is moved into `kept`
    first, so nothing of it is lost; remove() does the same. It loads (or stops) at the next start."""

    def __init__(self, plugins: Path, work: Path, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._plugins = plugins
        self._work = work
        self._transport = transport

    def installed(self) -> dict[str, str]:
        """The plugins in the folder: id → version."""
        found = {}
        for file in self._plugins.glob(f"*/{MANIFEST}"):
            try:
                manifest = PluginManifest.read(file)
            except (ValueError, OSError):
                continue
            found[manifest.id] = manifest.version
        return found

    async def install(self, plugin: ListedPlugin) -> Path:
        """The plugin's folder in the plugins folder."""
        if not plugin.download.startswith("https://"):
            raise RuntimeError("its download isn't an https address: not downloaded")
        self._work.mkdir(parents=True, exist_ok=True)
        archive = self._work / f"{plugin.id}.zip"
        sha, size = hashlib.sha256(), 0
        try:
            async with web_client(self._transport, timeout=60, follow_redirects=True) as client:
                async with client.stream("GET", plugin.download) as download:
                    download.raise_for_status()
                    with archive.open("wb") as out:
                        async for part in download.aiter_bytes(1 << 20):
                            size += len(part)
                            if size > LARGEST:
                                raise RuntimeError("the download is bigger than 50 MB: not a plugin")
                            sha.update(part)
                            out.write(part)
            if plugin.sha256 and sha.hexdigest() != plugin.sha256:
                raise RuntimeError("the download isn't the file the listing names (its SHA-256 differs)")
            return await asyncio.to_thread(self._put_in, archive, plugin)
        except httpx.HTTPError as e:
            raise RuntimeError(f"the download failed ({web_error(e)})") from None
        finally:
            archive.unlink(missing_ok=True)

    def _put_in(self, archive: Path, plugin: ListedPlugin) -> Path:
        unpacked = self._work / f"{plugin.id}.unpacked"
        shutil.rmtree(unpacked, ignore_errors=True)
        try:
            try:
                with zipfile.ZipFile(archive) as packed:
                    entries = packed.infolist()
                    if len(entries) > MOST_FILES or sum(e.file_size for e in entries) > LARGEST_UNPACKED:
                        raise RuntimeError("the download unpacks to more than 200 MB or 10000 files: not a plugin")
                    packed.extractall(unpacked)  # zipfile drops "..", drive letters and leading slashes
            except zipfile.BadZipFile:
                raise RuntimeError("the download isn't a zip file") from None
            found = sorted(unpacked.glob(MANIFEST)) or sorted(unpacked.glob(f"*/{MANIFEST}"))
            if not found:
                raise RuntimeError("the download has no plugin.json in it")
            manifest = PluginManifest.read(found[0])
            if manifest.id != plugin.id:
                raise RuntimeError(f"the download is the plugin {manifest.id}, not {plugin.id}")
            if version_numbers(manifest.version) != version_numbers(plugin.version):
                raise RuntimeError(f"the download is version {manifest.version}, the listing says {plugin.version}")
            target = self._plugins / plugin.id
            if target.exists():
                self._keep(target, plugin.id)
            self._plugins.mkdir(parents=True, exist_ok=True)
            shutil.move(str(found[0].parent), str(target))
            return target
        finally:
            shutil.rmtree(unpacked, ignore_errors=True)

    def remove(self, plugin_id: str) -> Path:
        """Takes the plugin out of the plugins folder (it stops at the next start); its folder is kept in
        `kept`, where it is. Its settings (config/plugins/<id>.json) and keys stay: installing it again finds
        them."""
        target = self._plugins / plugin_id
        if not (target / MANIFEST).is_file():
            raise RuntimeError(f"there is no plugin folder {plugin_id} in the plugins folder")
        return self._keep(target, plugin_id)

    def _keep(self, target: Path, plugin_id: str) -> Path:
        """Moves a plugin folder into `kept` (named after its id and version; an older copy of the same version
        is replaced)."""
        old = PluginManifest.read(target / MANIFEST).version if (target / MANIFEST).is_file() else "old"
        kept = self._work / "kept" / f"{plugin_id}-{old}"
        shutil.rmtree(kept, ignore_errors=True)
        kept.parent.mkdir(parents=True, exist_ok=True)
        target.rename(kept)
        return kept
