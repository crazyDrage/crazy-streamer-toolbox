from streamer_toolbox.connections.obs.boxes.obs_input_box import ObsInputBox, Call


class SetText(ObsInputBox):
    name = "set_text"
    label = "Set text"
    help = "Puts text into a Text source (e.g. 'Tracking Lost!')"
    group = "Sources"

    def __init__(self, call: Call) -> None:
        super().__init__(call)
        self.options = {"source": self.text_names}

    async def run(self, source: str, text: str = "") -> None:
        await self._request("SetInputSettings", {"inputName": source, "inputSettings": {"text": str(text)}})
