from typing import TYPE_CHECKING, Any

from streamer_toolbox.connections.sammi.boxes.sammi_box import DECK_STATES, SammiBox
from streamer_toolbox.core.actions.fixed_choices import fixed_choices

if TYPE_CHECKING:
    from streamer_toolbox.connections.sammi_connection import SammiConnection


class DeckOnOff(SammiBox):
    name = "set_deck"
    label = "Deck on / off"
    help = "Switches a SAMMI deck on, off or the other way (toggle)"
    group = "Decks"

    def __init__(self, sammi: "SammiConnection") -> None:
        super().__init__(sammi)
        self.options = {"deck": self.deck_names, "state": fixed_choices(DECK_STATES.keys())}

    async def run(self, deck: str, state: str = "on") -> Any:
        if state not in DECK_STATES:
            raise ValueError(f"state must be one of {', '.join(DECK_STATES)}, got {state!r}")
        return await self._sammi.send({"request": "changeDeckStatus", "deckID": deck, "status": DECK_STATES[state]})
