from typing import Any

from streamer_toolbox.connections.sammi.boxes.sammi_box import SammiBox


class GetDecks(SammiBox):
    name = "get_decks"
    label = "Get decks"
    help = "Every SAMMI deck with its buttons (name, id, on/off, buttons)"
    group = "Decks"
    live = True

    async def run(self) -> list[dict[str, Any]]:
        return await self._sammi.decks.summary()
