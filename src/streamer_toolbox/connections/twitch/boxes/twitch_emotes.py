import asyncio
import json
import logging
from typing import Any

from streamer_toolbox.core.flows.current_box import current_box
from streamer_toolbox.core.interfaces.box import Box
from streamer_toolbox.core.media.media_buffer import FOLDER, MediaBuffer

log = logging.getLogger(__name__)

# Twitch's address of an emote's picture: "default" is the moving one when it moves, 3.0 the biggest
EMOTE_PICTURE = "https://static-cdn.jtvnw.net/emoticons/v2/{id}/default/{theme}/3.0"
THEMES = ("dark", "light")
# the kept pictures (his "we save bandwidth even with a few emotes"): a few KB each; never forever (his round 90)
KEEP_MB, FILE_MB, KEEP_DAYS = 100.0, 5.0, 30.0
FOLDER_HINT = ("Where the pictures are kept on this PC. Boxes with the same folder share them (an emote is "
               "downloaded once for every flow). Empty = this box's own folder")


def checked_folder(folder: str) -> str:
    """A shared folder's name as Keep media locally takes it ("" = the box's own); a wrong one stops the box."""
    folder = str(folder or "").strip()
    if folder and not FOLDER.fullmatch(folder):
        raise ValueError(f"the folder name {folder!r} may only have letters, digits, _ and - (40 at most)")
    return folder


class TwitchEmotes(Box):
    """The emotes of a Twitch chat message as an emoji dictionary, {"Kappa": its picture's address} (his
    2026-11-16: "twitch emoji list, convert to {"emoji_text": "picture_url"}"), for an event's `emoji_dict`
    value: a text in the widget editor shows each word of the dictionary as its picture.

    It asks Twitch nothing: Twitch's chat says which words of a message are emotes (Chat gives them as
    `emotes`), the channel's own, Twitch's global ones and the ones a viewer has from other channels alike.
    `keep` (on): each picture is downloaded once and kept on this PC (MediaBuffer, like Keep media locally;
    his "we save bandwidth even with a few emotes"), the dictionary then has the toolbox's addresses. `folder`
    (his 11-16: "give them a folder name ... in case someone wants to use it without our flow"): twitch_emotes,
    shared by every box that names it; empty = the box's own. A picture
    that can't be kept keeps its Twitch address. Only Twitch: another platform's emotes get a box of their own
    (his round 90)."""

    name = "emotes"
    label = "Twitch emotes"
    help = ("The emotes of a Twitch chat message as an emoji dictionary: each emote's name and its picture's "
            "address. For an event's emoji_dict value: a text shows those words as their pictures")
    outputs = {"emoji_dict": "object"}
    group = "Chat"
    labels = {"emotes": "Emotes of the message", "keep": "Keep on this PC", "folder": "Folder"}
    hints = {"emotes": "Chat's emotes (a wire from the Start box's emotes). Only Twitch's: check the platform "
                       "before. None: an empty dictionary",
             "theme": "The pictures for a dark or a light background (only some emotes differ)",
             "keep": f"On: each picture is downloaded once and kept on this PC (at most {KEEP_MB:.0f} MB, "
                     f"{KEEP_DAYS:.0f} days), so it isn't loaded from Twitch again",
             "folder": FOLDER_HINT}
    options = {"theme": lambda: _themes()}

    def __init__(self, buffer: MediaBuffer | None = None) -> None:
        self._buffer = buffer

    async def run(self, emotes: Any = None, theme: str = THEMES[0], keep: bool = True,
                  folder: str = "twitch_emotes") -> dict[str, Any]:
        folder = checked_folder(folder)
        if theme not in THEMES:
            raise ValueError(f"the theme is dark or light, not {theme!r}")
        if isinstance(emotes, str):
            try:
                emotes = json.loads(emotes) if emotes.strip() else []
            except ValueError:
                raise ValueError("the emotes aren't a list (a wire from Chat's emotes)") from None
        found = {}
        for emote in emotes if isinstance(emotes, list) else []:
            if isinstance(emote, dict) and str(emote.get("name") or "").strip() and emote.get("id"):
                found[str(emote["name"]).strip()] = EMOTE_PICTURE.format(id=emote["id"], theme=theme)
        if keep and self._buffer is not None and found:
            box = current_box.get()
            kept = await asyncio.gather(*(self._kept(url, name, box, folder) for name, url in found.items()))
            found = dict(zip(found, kept))
        return {"emoji_dict": found}

    async def _kept(self, url: str, name: str, box: tuple[str, str] | None, folder: str) -> str:
        try:
            return (await self._buffer.keep(url, folder, KEEP_MB, FILE_MB, KEEP_DAYS, name, box)).address
        except Exception as e:  # noqa: BLE001 - Twitch's address still works
            log.warning("Twitch emotes: %s not kept (%s)", name, e)
            return url


async def _themes() -> list[str]:
    return list(THEMES)
