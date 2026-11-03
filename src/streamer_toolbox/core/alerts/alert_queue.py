import asyncio
import logging
import secrets
import time
import uuid
from collections import OrderedDict, deque
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from streamer_toolbox.core.alerts.alert import Alert
from streamer_toolbox.core.files.file_types import VIDEO_TYPES
from streamer_toolbox.core.overlay.sent_messages import SentMessages

log = logging.getLogger(__name__)

Sleep = Callable[[float], Awaitable[None]]
FILE_URL = "/overlay/file/"
RESEND_SECONDS = 60  # an alert older than this isn't shown to a page that comes back: it would be out of place


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
        # alerts that didn't reach OBS: no page listening, or one that didn't confirm it (api/overlay_line.py):
        # ("21:14:05", its text, its id), the newest last. A page that comes back gets them again (self.sent).
        self.missed: deque[tuple[str, str, int]] = deque(maxlen=20)
        self.sent = SentMessages(RESEND_SECONDS)
        self.on_change: Callable[[], None] | None = None  # the line changed (AlertBackup writes it down)

    @property
    def overlays(self) -> int:
        """How many overlay pages are listening right now (Browser sources; the toolbox's preview isn't one)."""
        return len(self._inboxes - self._previews)

    @property
    def waiting(self) -> int:
        return len(self._waiting)

    def listen(self, preview: bool = False) -> asyncio.Queue:
        """An inbox for one overlay page: it gets {"type": "alert", "alert": {...}} and {"type": "clear"}, each
        with its "id"."""
        inbox: asyncio.Queue = asyncio.Queue()
        self._inboxes.add(inbox)
        if preview:
            self._previews.add(inbox)
        return inbox

    def greeting(self, run: str | None = None, after: int | None = None) -> list[dict[str, Any]]:
        """What a page gets first on its line: {"type": "hello"} (the run, the newest id), and for a page that
        comes back (after: the last id it got) what it missed."""
        return [self.sent.hello()] + (self.sent.since(run, after) if after is not None else [])

    def stop_listening(self, inbox: asyncio.Queue) -> None:
        self._inboxes.discard(inbox)
        self._previews.discard(inbox)

    def not_arrived(self, message: dict[str, Any]) -> None:
        """An overlay page in OBS didn't confirm this message (its line broke): kept and logged."""
        if message.get("type") != "alert":
            return
        self._missed(message["alert"].get("text"), "its line broke", message.get("id", 0))

    def arrived(self, message: dict[str, Any]) -> None:
        """A page confirmed this message: an alert that was missed came through after all (sent again)."""
        for entry in [entry for entry in self.missed if entry[2] == message.get("id")]:
            self.missed.remove(entry)
            log.info("alert %r reached an overlay in OBS late (sent again)", entry[1])

    def _missed(self, text: str, why: str, id_: int) -> None:
        if any(entry[2] == id_ for entry in self.missed):  # two pages missed it: once is enough
            return
        text = text or "(no text)"
        self.missed.append((time.strftime("%H:%M:%S"), text, id_))
        log.warning("alert %r didn't reach an overlay in OBS (%s)", text, why)

    async def show(self, alert: Alert, wait: bool = False) -> int:
        """Puts the alert in the line; gives how many are in front of it. wait: until it has been shown.
        A picture or sound that isn't there fails here, where the box can say so."""
        _check_files(alert)
        in_front = len(self._waiting) + (1 if self._showing else 0)
        done = asyncio.Event()
        self._waiting.append((alert, done))
        self._changed()
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
        self._changed()
        return dropped

    def state(self) -> dict[str, Any]:
        """The line for a backup file: the alerts still waiting, the messages of the last minute (with the
        files their random names stand for) and the numbers."""
        sent = self.sent.state()
        named = {url[len(FILE_URL):] for _, _, message in sent["kept"] for url in
                 (message.get("alert", {}).get("image"), message.get("alert", {}).get("sound"))
                 if url and url.startswith(FILE_URL)}
        return {"waiting": [alert.to_dict() for alert, _ in self._waiting], "sent": sent,
                "files": {token: str(file) for token, file in self._files.items() if token in named}}

    def restore(self, state: dict[str, Any]) -> None:
        """Goes on from a backup (in the running event loop): the waiting alerts play, the numbers go on. An
        alert whose picture or sound is gone by now is left out."""
        self.sent.restore(state["sent"])
        self._files.update({token: Path(file) for token, file in state.get("files", {}).items()})
        for data in state.get("waiting", []):
            alert = Alert.from_dict(data)
            try:
                _check_files(alert)
            except FileNotFoundError as e:
                log.warning("a kept alert is left out: %s", e)
                continue
            self._waiting.append((alert, asyncio.Event()))
        if self._waiting and self._player is None:
            self._player = asyncio.create_task(self._play())

    def _changed(self) -> None:
        if self.on_change is not None:
            self.on_change()

    def file(self, token: str) -> Path | None:
        """The file a /overlay/file/<token> name stands for, None if it never did or is too old."""
        return self._files.get(token)

    async def _play(self) -> None:
        try:
            while self._waiting:
                alert, done = self._waiting.popleft()
                self._showing = True
                try:
                    sent = self._tell({"type": "alert", "alert": self.payload(alert)})
                    self._changed()
                    if not self.overlays:
                        self._missed(alert.text, "no Browser source was listening", sent["id"])
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

    def _tell(self, message: dict[str, Any]) -> dict[str, Any]:
        stamped = self.sent.stamp(message)
        for inbox in self._inboxes:
            inbox.put_nowait(stamped)
        return stamped


def _check_files(alert: Alert) -> None:
    for what, file in (("picture", alert.image), ("sound", alert.sound)):
        if file and not Path(file).is_file():
            raise FileNotFoundError(f"the alert's {what} isn't there: {file}")
