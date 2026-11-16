import asyncio
import logging
import re
from collections.abc import Callable
from typing import Any

from streamer_toolbox.connections.twitch.boxes.twitch_emotes import (FILE_MB, FOLDER_HINT, KEEP_DAYS, KEEP_MB,
                                                                    checked_folder)
from streamer_toolbox.core.flows.current_box import current_box
from streamer_toolbox.core.interfaces.box import Box
from streamer_toolbox.core.media.media_buffer import MediaBuffer
from streamer_toolbox.core.widgets.emote_lookup import EmoteLookup
from streamer_toolbox.core.widgets.kept_answers import KeptAnswers

log = logging.getLogger(__name__)


class BttvEmotes(Box):
    """The BetterTTV emotes of a chat message as an emoji dictionary of their own (his 11-16: "add the betterTTV
    one now", "I would do a different dict, and then add the 2 dicts together"): each whole word of the message
    that is one of your channel's BetterTTV emotes (its own and shared ones) or a global one, and its picture.
    Join objects puts it together with Twitch emotes' for Send chat's emoji_dict.

    BetterTTV is asked once in a while (`lookup` keeps its answers in `kept`, a few hours), not per message; when
    it can't be reached the dictionary goes on as it came: a chat never stops for it. `keep` (on): the pictures are
    kept on this PC like Twitch emotes', in `folder` (bttv_emotes, shared by every box that names it; empty = the
    box's own; his 11-16: "in case someone wants to use it without our flow"). `own_id()`: your channel's Twitch
    id (the Twitch login)."""

    name = "bttv_emotes"
    label = "BetterTTV emotes"
    help = ("The BetterTTV emotes of a chat message (your channel's and the global ones) as an emoji dictionary: "
            "each such word and its picture. Join objects adds it to Twitch emotes' one")
    outputs = {"emoji_dict": "object"}
    group = "Chat"
    labels = {"message": "Message", "channel": "Twitch channel id", "keep": "Keep on this PC", "folder": "Folder"}
    hints = {"message": "The chat message (a wire from the Start box's message)",
             "channel": "Whose BetterTTV emotes: a Twitch user id. Empty: your channel's",
             "keep": f"On: each picture is downloaded once and kept on this PC (at most {KEEP_MB:.0f} MB, "
                     f"{KEEP_DAYS:.0f} days)",
             "folder": FOLDER_HINT}

    def __init__(self, lookup: EmoteLookup, kept: KeptAnswers, own_id: Callable[[], str],
                 buffer: MediaBuffer | None = None) -> None:
        self._lookup = lookup
        self._kept = kept
        self._own_id = own_id
        self._buffer = buffer

    async def run(self, message: Any = "", channel: str = "", keep: bool = True,
                  folder: str = "bttv_emotes") -> dict[str, Any]:
        folder = checked_folder(folder)
        words = set(re.findall(r"\S+", str(message or "")))
        if not words:
            return {"emoji_dict": {}}
        try:
            known = await self._lookup.bttv(str(channel or "").strip() or self._own_id(), self._kept)
        except Exception as e:  # noqa: BLE001 - a chat goes on without them
            log.warning("BetterTTV emotes: not asked (%s)", e)
            return {"emoji_dict": {}}
        found = {word: known[word] for word in sorted(words) if word in known}
        if keep and self._buffer is not None and found:
            box = current_box.get()
            kept = await asyncio.gather(*(self._kept_picture(url, word, box, folder) for word, url in found.items()))
            found = dict(zip(found, kept))
        return {"emoji_dict": found}

    async def _kept_picture(self, url: str, name: str, box: tuple[str, str] | None, folder: str) -> str:
        try:
            return (await self._buffer.keep(url, folder, KEEP_MB, FILE_MB, KEEP_DAYS, name, box)).address
        except Exception as e:  # noqa: BLE001 - BetterTTV's address still works
            log.warning("BetterTTV emotes: %s not kept (%s)", name, e)
            return url
