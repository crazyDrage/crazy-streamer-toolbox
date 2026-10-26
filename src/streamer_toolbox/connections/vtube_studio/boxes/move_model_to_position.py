from typing import TYPE_CHECKING

from streamer_toolbox.connections.vtube_studio.vts_position import VtsPosition
from streamer_toolbox.core.data.box_value import to_bool
from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vts_connection import VtsConnection


class MoveModelToPosition(Box):
    name = "move_model_to"
    label = "Move model to position"
    help = "Moves the model to a position, e.g. a variable made by Get model position. load_model: if the " \
           "position belongs to another model, load that model first"
    group = "Model position"
    capture = "vts.get_model_position:position"

    def __init__(self, vts: "VtsConnection") -> None:
        self._vts = vts

    async def run(self, position: dict, seconds: float = 1.0, load_model: bool = False) -> None:
        model = position.get("model") if isinstance(position, dict) else None
        if to_bool(load_model) and model:
            await self._vts.ensure_model(model)
        await self._vts.move(VtsPosition.from_dict(position), seconds)
