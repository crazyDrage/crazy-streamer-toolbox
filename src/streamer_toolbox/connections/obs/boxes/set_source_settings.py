from typing import Any

from streamer_toolbox.connections.obs.boxes.obs_input_box import ObsInputBox, Call, _source_name
from streamer_toolbox.core.data.box_value import to_kind


class SetSourceSettings(ObsInputBox):
    name = "set_source_settings"
    label = "Set source settings"
    help = 'Changes some settings of a source; settings = an object like {"url": "..."}. The others stay'
    group = "Sources"

    def __init__(self, call: Call) -> None:
        super().__init__(call)
        self.options = {"source": self.input_names}

    async def run(self, source: str, settings: Any) -> None:
        try:
            changes = to_kind(settings, "object")
        except ValueError:
            raise ValueError(f"settings must be an object like {{\"text\": \"hi\"}}, not {settings!r}") from None
        await self._request("SetInputSettings", {"inputName": _source_name(source), "inputSettings": changes,
                                                 "overlay": True})
