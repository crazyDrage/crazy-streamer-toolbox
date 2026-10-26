from typing import Any

from streamer_toolbox.connections.obs.boxes.obs_input_box import ObsInputBox, Call, _source_name


class GetSourceSettings(ObsInputBox):
    name = "get_source_settings"
    label = "Get source settings"
    help = "A source's settings as an object (what its Properties window shows, e.g. file, text, url)"
    group = "Sources"

    def __init__(self, call: Call) -> None:
        super().__init__(call)
        self.options = {"source": self.input_names}

    async def run(self, source: str) -> dict[str, Any]:
        name = _source_name(source)
        return (await self._request("GetInputSettings", {"inputName": name})).get("inputSettings", {})
