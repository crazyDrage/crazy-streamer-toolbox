import asyncio
import hashlib
import ipaddress
import json
import logging
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

from streamer_toolbox.core.files.write_whole import write_whole
from streamer_toolbox.core.media.kept_media import Kept
from streamer_toolbox.core.web.web_client import web_client

log = logging.getLogger(__name__)

ROUTE = "/media/kept"  # + /<folder>/<file>: where overlays load a kept file from (api/media_router.py)
INDEX = "index.json"
FOLDER = re.compile(r"[\w-]{1,40}")
FILE = re.compile(r"[0-9a-f]{32}\.\w{2,5}")
# what is kept: pictures and videos (no SVG: opened on the toolbox's own address it could run code)
KINDS = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp",
         "image/apng": ".apng", "image/avif": ".avif", "video/webm": ".webm", "video/mp4": ".mp4"}
MB = 1024 * 1024
DAY = 24 * 60 * 60
USED_EVERY = 60 * 60  # "last used" is written down at most once an hour per file


class MediaBuffer:
    """Pictures and videos from the web kept on this PC (his idea of 11-14: "a media buffer system, where we
    remember an url, and save it localy"). `keep(url)` downloads it once into cache/media/<folder>/, named after
    the address (the same address = the same file), and gives where it lies; the toolbox serves it at
    /media/kept/<folder>/<file>, and only files of a folder's index. Each folder has the limits the box that
    last kept something in it gave: the whole folder's size (the longest unused go first), one file's size,
    and how many days a file is good for (0 = while there is room). A changed profile picture has another
    address, so it is a new file; the old one goes when room is needed.

    Only http(s) addresses on the internet: not this PC, not the home network (a flow from someone else must
    not reach the router through the toolbox)."""

    def __init__(self, folder: Path, transport: httpx.AsyncBaseTransport | None = None,
                 clock: Callable[[], float] = time.time) -> None:
        self._folder = folder.resolve()  # a whole path: OBS needs one for `file`
        self._transport = transport
        self._clock = clock
        self._locks: dict[tuple[str, str], asyncio.Lock] = {}

    async def keep(self, url: str, folder: str = "media", max_mb: float = 500, file_mb: float = 20,
                   days: float = 0) -> Kept:
        url = str(url or "").strip()
        _check_url(url)
        folder = _check_folder(folder)
        if file_mb <= 0 or max_mb <= 0:
            raise ValueError("the sizes must be more than 0 MB")
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]
        async with self._locks.setdefault((folder, key), asyncio.Lock()):
            index = self._index(folder)
            index["limits"] = {"max_mb": max_mb, "file_mb": file_mb, "days": days}
            found = self._good(folder, index, key, days)
            if found is None:
                found = await self._download(folder, url, key, int(file_mb * MB))
                index["files"][found.name] = {"url": url, "fetched": self._clock(), "used": self._clock(),
                                              "size": found.stat().st_size}
            else:
                index["files"][found.name]["used"] = self._clock()
            self._tidy(folder, index, keeping=found.name)
            self._save(folder, index)
        return Kept(f"{ROUTE}/{folder}/{found.name}", found)

    def find(self, folder: str, file: str) -> Path | None:
        """A kept file for the route: only one of that folder's index, and only while it is good."""
        if not FOLDER.fullmatch(folder) or not FILE.fullmatch(file):
            return None
        index = self._index(folder)
        entry = index["files"].get(file)
        path = self._folder / folder / file
        if entry is None or not path.is_file():
            return None
        days = float(index.get("limits", {}).get("days", 0) or 0)
        if days and self._clock() - float(entry.get("fetched", 0)) >= days * DAY:
            return None
        if self._clock() - float(entry.get("used", 0)) >= USED_EVERY:
            entry["used"] = self._clock()
            self._save(folder, index)
        return path

    # ---- inside ----

    def _good(self, folder: str, index: dict[str, Any], key: str, days: float) -> Path | None:
        for name, entry in index["files"].items():
            if name.startswith(key + "."):
                path = self._folder / folder / name
                fresh = not days or self._clock() - float(entry.get("fetched", 0)) < days * DAY
                return path if fresh and path.is_file() else None
        return None

    async def _download(self, folder: str, url: str, key: str, most: int) -> Path:
        async def checked(request: httpx.Request) -> None:  # every step of a redirect too
            _check_url(str(request.url))

        async with web_client(self._transport, timeout=15, follow_redirects=True, max_redirects=5,
                              event_hooks={"request": [checked]}) as client:
            async with client.stream("GET", url) as answer:
                if answer.status_code != 200:
                    raise ValueError(f"the address answered {answer.status_code}")
                kind = answer.headers.get("content-type", "").split(";")[0].strip().casefold()
                ending = KINDS.get(kind)
                if ending is None:
                    raise ValueError(f"not a picture or video ({kind or 'no type given'})")
                if int(answer.headers.get("content-length") or 0) > most:
                    raise ValueError(f"bigger than {most / MB:g} MB")
                data = bytearray()
                async for chunk in answer.aiter_bytes():
                    data += chunk
                    if len(data) > most:
                        raise ValueError(f"bigger than {most / MB:g} MB")
        path = self._folder / folder / f"{key}{ending}"
        path.parent.mkdir(parents=True, exist_ok=True)
        part = path.with_suffix(path.suffix + ".part")
        part.write_bytes(bytes(data))
        part.replace(path)
        for other in path.parent.glob(f"{key}.*"):  # the same address came back as another kind
            if other != path and other.suffix != ".part":
                other.unlink(missing_ok=True)
        return path

    def _tidy(self, folder: str, index: dict[str, Any], keeping: str) -> None:
        """Out with what is too old, then the longest unused until the folder fits (the file just kept stays)."""
        limits = index["limits"]
        days, most = float(limits.get("days", 0) or 0), float(limits.get("max_mb", 500)) * MB
        files: dict[str, dict[str, Any]] = index["files"]
        for name in list(files):
            if not (self._folder / folder / name).is_file():
                del files[name]
            elif days and name != keeping and self._clock() - float(files[name].get("fetched", 0)) >= days * DAY:
                self._drop(folder, files, name)
        total = sum(int(entry.get("size", 0)) for entry in files.values())
        for name in sorted(files, key=lambda n: float(files[n].get("used", 0))):
            if total <= most:
                break
            if name != keeping:
                total -= int(files[name].get("size", 0))
                self._drop(folder, files, name)

    def _drop(self, folder: str, files: dict[str, Any], name: str) -> None:
        (self._folder / folder / name).unlink(missing_ok=True)
        del files[name]

    def _index(self, folder: str) -> dict[str, Any]:
        path = self._folder / folder / INDEX
        try:
            data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
            files = {str(k): dict(v) for k, v in dict(data.get("files", {})).items() if FILE.fullmatch(str(k))}
            return {"limits": dict(data.get("limits", {})), "files": files}
        except (OSError, ValueError, TypeError, AttributeError):  # an unreadable index: the files come again
            log.warning("media buffer: %s can't be read, starting it again", path)
            return {"limits": {}, "files": {}}

    def _save(self, folder: str, index: dict[str, Any]) -> None:
        path = self._folder / folder / INDEX
        path.parent.mkdir(parents=True, exist_ok=True)
        write_whole(path, json.dumps(index, ensure_ascii=False, indent=1))


def _check_folder(folder: str) -> str:
    folder = str(folder or "").strip() or "media"
    if not FOLDER.fullmatch(folder):
        raise ValueError(f"the folder name {folder!r} may only have letters, digits, _ and - (40 at most)")
    return folder


def _check_url(url: str) -> None:
    if not url:
        raise ValueError("which address? (it is empty)")
    parts = urlsplit(url)
    if parts.scheme.casefold() not in ("http", "https") or not parts.hostname:
        raise ValueError(f"only web addresses (http / https) are kept, not {url[:80]!r}")
    host = parts.hostname.casefold().rstrip(".")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if "." not in host or host.endswith((".local", ".localhost", ".lan", ".home", ".internal")):
            raise ValueError(f"{host} is no address on the internet") from None
        return
    if not address.is_global:
        raise ValueError(f"{host} is on this PC or the home network: not kept")
