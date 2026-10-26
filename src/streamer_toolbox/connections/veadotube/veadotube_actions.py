from streamer_toolbox.connections.veadotube.boxes.get_state import GetState
from streamer_toolbox.connections.veadotube.boxes.put_state_on_top import PutStateOnTop
from streamer_toolbox.connections.veadotube.boxes.set_state import SetState
from streamer_toolbox.connections.veadotube.boxes.show_state_for_a_while import ShowStateForAWhile
from streamer_toolbox.connections.veadotube.boxes.state_on_off import StateOnOff
from streamer_toolbox.connections.veadotube.boxes.take_state_off import TakeStateOff
from streamer_toolbox.connections.veadotube.veadotube_client import VeadotubeClient
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class VeadotubeActions:
    """veadotube mini's boxes: the avatar's states by name (the picker lists them from the running program).
    veadotube keeps a stack of states and shows the top one: Set state replaces it, Show state for a while puts
    one on top and takes it off again, so what was shown before comes back by itself.

    One Box class per box, in boxes/."""

    def __init__(self, client: VeadotubeClient) -> None:
        self._client = client

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (SetState(self._client), ShowStateForAWhile(self._client), PutStateOnTop(self._client),
                    TakeStateOff(self._client), StateOnOff(self._client), GetState(self._client)):
            actions.add_box(box, "veadotube")
