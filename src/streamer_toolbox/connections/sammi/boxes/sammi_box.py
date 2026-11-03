from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.sammi_connection import SammiConnection

DECK_STATES = {"on": 1, "off": 0, "toggle": 2}  # changeDeckStatus


class SammiBox(Box):
    """What the SAMMI boxes share (not a box itself: it has no run): the connection (its send / get go to
    SAMMI's Local API), and the pickers that read SAMMI's decks and buttons each time a box form opens."""

    def __init__(self, sammi: "SammiConnection") -> None:
        self._sammi = sammi

    async def buttons(self) -> dict[str, dict[str, str]]:
        return await self._sammi.decks.button_groups()

    async def buttons_and_global(self) -> dict[str, dict[str, str]]:
        return {"(global)": {"global": "global (not a button)"}} | await self._sammi.decks.button_groups()

    async def deck_names(self) -> dict[str, str]:
        return await self._sammi.decks.deck_choices()


def bgr(color: str) -> int:
    """#rrggbb (or rrggbb) to the decimal BGR number SAMMI wants."""
    text = str(color).strip().lstrip("#")
    if len(text) != 6 or any(c not in "0123456789abcdefABCDEF" for c in text):
        raise ValueError(f"colour {color!r}: use #rrggbb, e.g. #ff8800")
    r, g, b = int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)
    return b * 65536 + g * 256 + r
