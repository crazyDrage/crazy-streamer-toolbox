import asyncio

from streamer_toolbox.connections.veadotube.veadotube_client import VeadotubeClient
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class VeadotubeActions:
    """veadotube mini's boxes: the avatar's states by name (the picker lists them from the running program).
    veadotube keeps a stack of states and shows the top one: Set state replaces it, Show state for a while puts
    one on top and takes it off again, so what was shown before comes back by itself."""

    def __init__(self, client: VeadotubeClient) -> None:
        self._client = client

    def add_to(self, actions: ActionRegistry) -> None:
        state = {"options": {"state": self.state_names}}
        actions.add("veadotube.set_state", self.set_state, "Switches the avatar to a state", "Set state", **state)
        actions.add("veadotube.show_state", self.show_state, "Shows a state for some seconds, then goes back to "
                    "what was shown before", "Show state for a while", **state)
        actions.add("veadotube.push_state", self.push_state, "Puts a state on top (it shows) until Take state "
                    "off removes it", "Put state on top", group="Stack", **state)
        actions.add("veadotube.pop_state", self.pop_state, "Takes a state off again; what was under it shows",
                    "Take state off", group="Stack", **state)
        actions.add("veadotube.toggle_state", self.toggle_state, "Puts a state on top, or takes it off when it "
                    "is there", "State on / off", group="Stack", **state)
        actions.add("veadotube.get_state", self.get_state, "The name of the state the avatar shows now",
                    "Get state", outputs={"state": "text"})

    async def state_names(self) -> list[str]:
        try:
            return list((await self._client.refresh()).values())
        except ConnectionError:
            return []

    async def set_state(self, state: str) -> None:
        await self._client.tell("set", await self._id(state))

    async def show_state(self, state: str, seconds: float = 3.0) -> None:
        state_id = await self._id(state)
        await self._client.tell("push", state_id)
        try:
            await asyncio.sleep(max(float(seconds), 0))
        finally:
            await self._client.tell("pop", state_id)

    async def push_state(self, state: str) -> None:
        await self._client.tell("push", await self._id(state))

    async def pop_state(self, state: str) -> None:
        await self._client.tell("pop", await self._id(state))

    async def toggle_state(self, state: str) -> None:
        await self._client.tell("toggle", await self._id(state))

    async def get_state(self) -> dict[str, str]:
        if not self._client.current:
            raise ConnectionError("veadotube mini is not connected")
        return {"state": self._client.current}

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
