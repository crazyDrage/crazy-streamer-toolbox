from typing import TYPE_CHECKING, Any

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vts_connection import VtsConnection


class GetModelPosition(Box):
    name = "get_model_position"
    label = "Get model position"
    help = "Reads where the model is now and which model it is: {x, y, rotation, size, model}. Save it in a " \
           "variable to use it later"
    group = "Model position"
    live = True
    outputs = {"x": "number", "y": "number", "rotation": "number", "size": "number", "model": "text"}

    def __init__(self, vts: "VtsConnection") -> None:
        self._vts = vts

    async def run(self) -> dict[str, Any]:
        model, position = await self._vts.current_model()
        return {**position.to_dict(), "model": model}
