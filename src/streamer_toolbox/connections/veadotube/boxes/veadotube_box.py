from streamer_toolbox.connections.veadotube.veadotube_client import VeadotubeClient
from streamer_toolbox.core.interfaces.box import Box


class VeadotubeBox(Box):
    """What the veadotube boxes share (not a box itself: it has no run).

    veadotube mini's boxes: the avatar's states by name (the picker lists them from the running program).
    veadotube keeps a stack of states and shows the top one: Set state replaces it, Show state for a while puts
    one on top and takes it off again, so what was shown before comes back by itself."""

    def __init__(self, client: VeadotubeClient) -> None:
        self._client = client

    async def state_names(self) -> list[str]:
        try:
            return list((await self._client.refresh()).values())
        except ConnectionError:
            return []

    async def _id(self, name: str) -> str:
        wanted = str(name).strip()
        for states in (self._client.states, None):
            states = states if states is not None else await self._client.refresh()
            found = next((i for i, n in states.items() if n == wanted), None) or \
                next((i for i, n in states.items() if n.casefold() == wanted.casefold()), None) or \
                (wanted if wanted in states else None)
            if found is not None:
                return found
        raise KeyError(f"veadotube has no state named {wanted!r}")
