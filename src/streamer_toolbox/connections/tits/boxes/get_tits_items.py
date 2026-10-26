from typing import Any

from streamer_toolbox.connections.tits.boxes.tits_box import TitsBox


class GetTITSItems(TitsBox):
    name = "get_items"
    label = "Get T.I.T.S. items"
    help = "The items T.I.T.S. has now: their names and how many"
    live = True
    outputs = {"count": "number", "names": "list"}

    async def run(self) -> dict[str, Any]:
        names = sorted(await self._items(), key=str.casefold)
        return {"count": len(names), "names": names}
