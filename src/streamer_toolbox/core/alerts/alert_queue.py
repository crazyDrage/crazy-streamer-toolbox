import asyncio
import secrets
import uuid
from collections import OrderedDict, deque
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from streamer_toolbox.core.alerts.alert import Alert
from streamer_toolbox.core.files.file_types import VIDEO_TYPES

Sleep = Callable[[float], Awaitable[None]]
FILE_URL = "/overlay/file/"


class AlertQueue:
    """The alerts waiting for the overlay. They play one after the other, each for its seconds plus a short gap,
    and go to every overlay page that is listening (each Browser source in OBS holds a socket and gets an inbox
    here). Without an overlay an alert still takes its time, so the line keeps its rhythm.

    The overlay is a web page: it can't read this PC's files, and the toolbox must not hand out any path that is
    asked for. So each alert's picture and sound get a random name under /overlay/file/ that only stands for that
    file; the names of the latest `keep_files` files stay good (an alert in the line, a page that loads late)."""

    def __init__(self, gap: float = 0.5, sleep: Sleep = asyncio.sleep, keep_files: int = 60) -> None:
        self._gap = gap
        self._sleep = sleep
        self._keep_files = keep_files
        self._waiting: deque[tuple[Alert, asyncio.Event]] = deque()
        self._inboxes: set[asyncio.Queue] = set()
        self._previews: set[asyncio.Queue] = set()  # inboxes of preview pages: they get alerts, but aren't OBS
        self._files: OrderedDict[str, Path] = OrderedDict()
        self._player: asyncio.Task | None = None
        self._showing = False  # an alert is on the overlays right now (it's no longer in the line)

    @property
    def overlays(self) -> int:
        """How many overlay pages are listening right now (Browser sources; the toolbox's preview isn't one)."""
        return len(self._inboxes - self._previews)

    @property
    def waiting(self) -> int:
        return len(self._waiting)

    def listen(self, preview: bool = False) -> asyncio.Queue:
        """An inbox for one overlay page: it gets {"type": "alert", "alert": {...}} and {"type": "clear"}."""
        inbox: asyncio.Queue = asyncio.Queue()
        self._inboxes.add(inbox)
        if preview:
            self._previews.add(inbox)
        return inbox

    def stop_listening(self, inbox: asyncio.Queue) -> None:
        self._inboxes.discard(inbox)
        self._previews.discard(inbox)

    async def show(self, alert: Alert, wait: bool = False) -> int:
        """Puts the alert in the line; gives how many are in front of it. wait: until it has been shown.
        A picture or sound that isn't there fails here, where the box can say so."""
        _check_files(alert)
        in_front = len(self._waiting) + (1 if self._showing else 0)
        done = asyncio.Event()
        self._waiting.append((alert, done))
        if self._player is None:
            self._player = asyncio.create_task(self._play())
        if wait:
            await done.wait()
        return in_front

    def clear(self) -> int:
        """Empties the line and takes the alert that is showing away; gives how many were dropped."""
        dropped = len(self._waiting) + (1 if self._showing else 0)
        waiting, self._waiting = self._waiting, deque()
        for _, done in waiting:
            done.set()
        if self._player is not None:
            self._player.cancel()
            self._player = None
            self._showing = False
        self._tell({"type": "clear"})
        return dropped

    def file(self, token: str) -> Path | None:
        """The file a /overlay/file/<token> name stands for, None if it never did or is too old."""
        return self._files.get(token)

    async def _play(self) -> None:
        try:
            while self._waiting:
                alert, done = self._waiting.popleft()
                self._showing = True
                try:
                    self._tell({"type": "alert", "alert": self.payload(alert)})
                    await self._sleep(alert.shown_seconds + self._gap)
                finally:
                    done.set()
                self._showing = False
        finally:
            if self._player is asyncio.current_task():
                self._player = None
                self._showing = False

    def payload(self, alert: Alert) -> dict[str, Any]:
        """What an overlay page gets for one alert (also the look editor's frame, without the line): its files
        under their random names, never a path of this PC."""
        _check_files(alert)
        video = Path(alert.image).suffix.casefold() in VIDEO_TYPES and not alert.image.casefold().endswith(".gif")
        parts = list(alert.parts) or [{"kind": kind, "text": text} for kind, text in
                                      (("text", alert.text), ("message", alert.message)) if text]
        return {"id": uuid.uuid4().hex[:8], "text": alert.text, "message": alert.message, "parts": parts,
                "highlights": [h for h in alert.highlights if h],
                "image": self._url(alert.image), "video": bool(alert.image) and video,
                "sound": self._url(alert.sound), "seconds": alert.shown_seconds,
                "volume": max(0.0, min(float(alert.volume), 1.0)), "look": alert.look.to_dict()}

    def _url(self, file: str) -> str:
        if not file:
            return ""
        token = secrets.token_urlsafe(12) + Path(file).suffix.casefold()  # the ending tells the browser the kind
        self._files[token] = Path(file)
        while len(self._files) > self._keep_files:
            self._files.popitem(last=False)
        return FILE_URL + token

    def _tell(self, message: dict[str, Any]) -> None:
        for inbox in self._inboxes:
            inbox.put_nowait(message)


def _check_files(alert: Alert) -> None:
    for what, file in (("picture", alert.image), ("sound", alert.sound)):
        if file and not Path(file).is_file():
            raise FileNotFoundError(f"the alert's {what} isn't there: {file}")
