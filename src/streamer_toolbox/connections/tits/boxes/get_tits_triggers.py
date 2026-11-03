from typing import Any

from streamer_toolbox.connections.tits.boxes.tits_box import TitsBox


class GetTITSTriggers(TitsBox):
    name = "get_triggers"
    label = "Get T.I.T.S. triggers"
    help = "The triggers made in T.I.T.S.: their names and how many"
    live = True
    outputs = {"count": "number", "names": "list"}

    async def run(self) -> dict[str, Any]:
        names = sorted(await self._triggers(), key=str.casefold)
        return {"count": len(names), "names": names}
