import asyncio
import hashlib
import ipaddress
import json
import logging
import re
import shutil
import socket
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

from streamer_toolbox.core.files.write_whole import write_whole
from streamer_toolbox.core.media.kept_media import Kept
from streamer_toolbox.core.web.web_client import web_client

log = logging.getLogger(__name__)

# where overlays and OBS load a kept file from (api/media_router.py); the address is the file's place in
# cache/media/ (his 11-15: "every flow, and box in the flow should have an endpoint")
ROUTE = "/toolbox/media"
BOX_PLACE = "flows/box"  # + /<flow>/<box id>: a box's own folder
SHARED_PLACE = "shared"  # + /<folder>: a folder boxes share (the box's Folder field), or what Live / the API kept
INDEX = "index.json"
BOXES = "boxes.json"  # "<flow>/<box id>" -> the shared folder that box keeps in (only boxes with a Folder)
FOLDER = re.compile(r"[\w-]{1,40}")
FLOW = re.compile(r"[a-z0-9_]{1,100}")  # a flow's file name (FlowStore.NAME)
BOX = re.compile(r"[\w-]{1,40}")
CODE = 16  # hex digits of the address's hash at the front of a file's name: the same address = the same file
FILE = re.compile(rf"[0-9a-f]{{{CODE}}}(_[A-Za-z0-9-]{{1,40}})?\.\w{{2,5}}")
LATEST = re.compile(r"latest(\.\w{2,5})?")  # latest.png: the newest file a box (or a shared folder) kept
NOT_IN_NAME = re.compile(r"[^A-Za-z0-9-]+")
# what is kept: pictures and videos (no SVG: opened on the toolbox's own address it could run code)
KINDS = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp",
         "image/apng": ".apng", "image/avif": ".avif", "video/webm": ".webm", "video/mp4": ".mp4"}
MB = 1024 * 1024
DAY = 24 * 60 * 60
USED_EVERY = 60 * 60  # "last used" is written down at most once an hour per file
Resolve = Callable[[str], Awaitable[list[str]]]  # a host name -> its IP addresses


class MediaBuffer:
    """Pictures and videos from the web kept on this PC (his idea of 11-14: "a media buffer system, where we
    remember an url, and save it localy"). `keep(url)` downloads it once and gives where it lies. The address
    is the file's place under cache/media/ (his 11-15):

        /toolbox/media/flows/box/<flow>/<box id>/<code>_<name>.png   a box in a flow, its own folder
        /toolbox/media/flows/box/<flow>/<box id>/latest.png          the newest file that box kept
        /toolbox/media/shared/<folder>/<file>                        kept on Live / the API (folder "media")

    A box with a Folder keeps in shared/<folder>/ (pictures used in several flows are downloaded once), and its
    own address still leads there. <code> comes from the address (the same address = the same file), <name> is
    the box's File name (optional, e.g. the chatter's login). Only files of a folder's index are served.

    Each folder has the limits the box that last kept something in it gave: the whole folder's size (the
    longest unused go first), one file's size, and how many days a file is good for (0 = while there is room).
    A changed profile picture has another address, so it is a new file; the old one goes when room is needed.
    A box's own folder goes when Save flow leaves the box out or its flow is deleted (`forget`).

    Only http(s) addresses on the internet: not this PC, not the home network (a flow from someone else must
    not reach the router through the toolbox). A name is looked up first: one that points inside (localtest.me
    is 127.0.0.1) is refused too. Left open: a name server that answers differently a moment later (DNS
    rebinding) still gets through, as httpx looks the name up again."""

    def __init__(self, folder: Path, transport: httpx.AsyncBaseTransport | None = None,
                 clock: Callable[[], float] = time.time, resolve: Resolve | None = None) -> None:
        self._folder = folder.resolve()  # a whole path: OBS needs one for `file`
        self._transport = transport
        self._clock = clock
        self._resolve = resolve or _addresses
        self._locks: dict[tuple[str, str], asyncio.Lock] = {}

    async def keep(self, url: str, folder: str = "", max_mb: float = 500, file_mb: float = 20,
                   days: float = 0, name: str = "", box: tuple[str, str] | None = None) -> Kept:
        """box: (flow name, box id) of the box that keeps it; None on Live / the API."""
        url = str(url or "").strip()
        _check_url(url)
        folder = _check_folder(folder) if str(folder or "").strip() else ""
        if box is not None:
            box = _check_box(*box)
        if file_mb <= 0 or max_mb <= 0:
            raise ValueError("the sizes must be more than 0 MB")
        place = _own(box) if box is not None and not folder else f"{SHARED_PLACE}/{folder or 'media'}"
        if box is not None:
            self._map(box, folder)
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:CODE]
        async with self._locks.setdefault((place, key), asyncio.Lock()):
            index = self._index(place)
            index["limits"] = {"max_mb": max_mb, "file_mb": file_mb, "days": days}
            found = self._good(place, index, key, days)
            if found is None:
                found = await self._download(place, url, key, _name_part(name), int(file_mb * MB))
                index["files"][found.name] = {"url": url, "fetched": self._clock(), "used": self._clock(),
                                              "size": found.stat().st_size}
            else:
                index["files"][found.name]["used"] = self._clock()
            index["latest"][""] = found.name
            if box is not None:
                index["latest"]["/".join(box)] = found.name
            self._tidy(place, index, keeping=found.name)
            self._save(place, index)
        if box is not None:
            return Kept(f"{ROUTE}/{BOX_PLACE}/{box[0]}/{box[1]}/{found.name}", found)
        return Kept(f"{ROUTE}/{place}/{found.name}", found)

    def find_for_box(self, flow: str, box: str, file: str) -> Path | None:
        """A kept file at a box's address (latest.* = the newest it kept), only while it is good."""
        if not FLOW.fullmatch(flow) or not BOX.fullmatch(box):
            return None
        shared = self._boxes().get(f"{flow}/{box}")
        place = f"{SHARED_PLACE}/{shared}" if shared else _own((flow, box))
        return self._find(place, file, f"{flow}/{box}")

    def find_shared(self, folder: str, file: str) -> Path | None:
        """A kept file of a shared folder (latest.* = the newest anyone kept there)."""
        if not FOLDER.fullmatch(folder):
            return None
        return self._find(f"{SHARED_PLACE}/{folder}", file, "")

    def forget(self, flow: str, boxes: list[str]) -> None:
        """These boxes of the flow are gone (Save flow without them, the flow deleted): their own folders go;
        what they kept in a shared folder stays for the others, until room is needed."""
        if not FLOW.fullmatch(flow):
            return
        mapped = self._boxes()
        before = dict(mapped)
        for box in boxes:
            mapped.pop(f"{flow}/{box}", None)
            if BOX.fullmatch(box):
                shutil.rmtree(self._folder / _own((flow, box)), ignore_errors=True)
        flow_folder = self._folder / BOX_PLACE / flow
        if flow_folder.is_dir() and not any(flow_folder.iterdir()):
            flow_folder.rmdir()
        if mapped != before:
            self._save_boxes(mapped)

    # ---- inside ----

    def _find(self, place: str, file: str, latest_of: str) -> Path | None:
        index = self._index(place)
        if LATEST.fullmatch(file):
            file = index["latest"].get(latest_of, "")
        if not FILE.fullmatch(file):
            return None
        entry = index["files"].get(file)
        path = self._folder / place / file
        if entry is None or not path.is_file():
            return None
        days = float(index.get("limits", {}).get("days", 0) or 0)
        if days and self._clock() - float(entry.get("fetched", 0)) >= days * DAY:
            return None
        if self._clock() - float(entry.get("used", 0)) >= USED_EVERY:
            entry["used"] = self._clock()
            self._save(place, index)
        return path

    def _good(self, place: str, index: dict[str, Any], key: str, days: float) -> Path | None:
        for name, entry in index["files"].items():
            if name.startswith((key + ".", key + "_")):
                path = self._folder / place / name
                fresh = not days or self._clock() - float(entry.get("fetched", 0)) < days * DAY
                return path if fresh and path.is_file() else None
        return None

    async def _download(self, place: str, url: str, key: str, name: str, most: int) -> Path:
        async def checked(request: httpx.Request) -> None:  # every step of a redirect too
            _check_url(str(request.url))
            await self._check_name(request.url.host)

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
        path = self._folder / place / f"{key}{'_' + name if name else ''}{ending}"
        path.parent.mkdir(parents=True, exist_ok=True)
        part = path.with_suffix(path.suffix + ".part")
        part.write_bytes(bytes(data))
        part.replace(path)
        for other in [*path.parent.glob(f"{key}.*"), *path.parent.glob(f"{key}_*")]:  # an old name or kind
            if other != path and other.suffix != ".part":
                other.unlink(missing_ok=True)
        return path

    async def _check_name(self, host: str) -> None:
        try:
            ipaddress.ip_address(host)
            return  # an address itself: _check_url had it
        except ValueError:
            pass
        try:
            found = await self._resolve(host)
        except OSError as e:
            raise ValueError(f"{host} can't be found ({e})") from None
        for address in found:
            if not ipaddress.ip_address(address.split("%")[0]).is_global:
                raise ValueError(f"{host} points to this PC or the home network ({address}): not kept")
        if not found:
            raise ValueError(f"{host} can't be found")

    def _tidy(self, place: str, index: dict[str, Any], keeping: str) -> None:
        """Out with what is too old, then the longest unused until the folder fits (the file just kept stays)."""
        limits = index["limits"]
        days, most = float(limits.get("days", 0) or 0), float(limits.get("max_mb", 500)) * MB
        files: dict[str, dict[str, Any]] = index["files"]
        for name in list(files):
            if not (self._folder / place / name).is_file():
                del files[name]
            elif days and name != keeping and self._clock() - float(files[name].get("fetched", 0)) >= days * DAY:
                self._drop(place, index, name)
        total = sum(int(entry.get("size", 0)) for entry in files.values())
        for name in sorted(files, key=lambda n: float(files[n].get("used", 0))):
            if total <= most:
                break
            if name != keeping:
                total -= int(files[name].get("size", 0))
                self._drop(place, index, name)
        index["latest"] = {k: v for k, v in index["latest"].items() if v in files}

    def _drop(self, place: str, index: dict[str, Any], name: str) -> None:
        (self._folder / place / name).unlink(missing_ok=True)
        del index["files"][name]

    def _index(self, place: str) -> dict[str, Any]:
        path = self._folder / place / INDEX
        try:
            data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
            files = {str(k): dict(v) for k, v in dict(data.get("files", {})).items() if FILE.fullmatch(str(k))}
            latest = {str(k): str(v) for k, v in dict(data.get("latest", {})).items() if str(v) in files}
            return {"limits": dict(data.get("limits", {})), "files": files, "latest": latest}
        except (OSError, ValueError, TypeError, AttributeError):  # an unreadable index: the files come again
            log.warning("media buffer: %s can't be read, starting it again", path)
            return {"limits": {}, "files": {}, "latest": {}}

    def _save(self, place: str, index: dict[str, Any]) -> None:
        path = self._folder / place / INDEX
        path.parent.mkdir(parents=True, exist_ok=True)
        write_whole(path, json.dumps(index, ensure_ascii=False, indent=1))

    def _map(self, box: tuple[str, str], folder: str) -> None:
        """Which shared folder a box keeps in; written only when it changes."""
        mapped = self._boxes()
        key = "/".join(box)
        if mapped.get(key, "") != folder:
            if folder:
                mapped[key] = folder
            else:
                mapped.pop(key, None)
            self._save_boxes(mapped)

    def _boxes(self) -> dict[str, str]:
        path = self._folder / BOXES
        try:
            data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
            return {str(k): str(v) for k, v in dict(data).items() if FOLDER.fullmatch(str(v))}
        except (OSError, ValueError, TypeError):
            log.warning("media buffer: %s can't be read, starting it again", path)
            return {}

    def _save_boxes(self, mapped: dict[str, str]) -> None:
        self._folder.mkdir(parents=True, exist_ok=True)
        write_whole(self._folder / BOXES, json.dumps(mapped, ensure_ascii=False, indent=1))


def _own(box: tuple[str, str]) -> str:
    return f"{BOX_PLACE}/{box[0]}/{box[1]}"


def _check_box(flow: str, box: str) -> tuple[str, str]:
    if not FLOW.fullmatch(flow) or not BOX.fullmatch(box):
        raise ValueError(f"no folder for the box {box!r} of the flow {flow!r}")
    return flow, box


def _name_part(name: str) -> str:
    """The File name as a part of a file's name: letters, digits and -, at most 40 ("Kit Fox!" -> "Kit-Fox")."""
    return NOT_IN_NAME.sub("-", str(name or "")).strip("-")[:40].strip("-")


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


async def _addresses(host: str) -> list[str]:
    infos = await asyncio.get_running_loop().getaddrinfo(host, None, type=socket.SOCK_STREAM)
    return [str(info[4][0]) for info in infos]
