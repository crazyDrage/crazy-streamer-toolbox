from typing import TYPE_CHECKING

from streamer_toolbox.connections.sammi.boxes.sammi_box import SammiBox

if TYPE_CHECKING:
    from streamer_toolbox.connections.sammi_connection import SammiConnection


class IsDeckOn(SammiBox):
    name = "get_deck_on"
    label = "Is deck on?"
    help = "Whether a SAMMI deck is on"
    group = "Decks"

    def __init__(self, sammi: "SammiConnection") -> None:
        super().__init__(sammi)
        self.options = {"deck": self.deck_names}

    async def run(self, deck: str) -> bool:
        return bool(await self._sammi.get(request="getDeckStatus", deckID=deck))
