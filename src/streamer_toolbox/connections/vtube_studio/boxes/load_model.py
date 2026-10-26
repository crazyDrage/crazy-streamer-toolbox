from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vts_connection import VtsConnection


class LoadModel(Box):
    name = "load_model"
    label = "Load model"
    help = "Loads a model by name"
    group = "Model"
    labels = {"wait_until_loaded": "Wait until it's loaded", "seconds": "Give up after (s)"}
    hints = {"wait_until_loaded": "On: the box ends when VTube Studio shows the new model, so the "
                                  "next boxes (e.g. move it) work on that one"}

    def __init__(self, vts: "VtsConnection") -> None:
        self._vts = vts
        self.options = {"model": self._vts.model_names}

    async def run(self, model: str, wait_until_loaded: bool = True, seconds: float = 20.0) -> None:
        return await self._vts.load_model(model, wait_until_loaded, seconds)
