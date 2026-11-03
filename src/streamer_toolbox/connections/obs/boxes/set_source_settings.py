from typing import Any

from streamer_toolbox.connections.obs.boxes.obs_input_box import ObsInputBox, Call, _source_name
from streamer_toolbox.core.data.box_value import to_kind


class SetSourceSettings(ObsInputBox):
    name = "set_source_settings"
    label = "Set source settings"
    help = 'Changes some settings of a source: Get settings gives a line per setting it has (url, width, ...); ' \
           'fill or wire the ones to change. Or settings = an object like {"url": "..."}. The others stay'
    group = "Sources"
    named_lines = True  # one line per setting (his round 81); an empty line changes nothing
    lines_from = "obs.get_source_settings:Get settings"
    hints = {"settings": 'optional: an object like {"url": "..."}; the lines below are added to it'}

    def __init__(self, call: Call) -> None:
        super().__init__(call)
        self.options = {"source": self.input_names}

    async def run(self, source: str, settings: Any = None, **lines: Any) -> None:
        try:
            changes = {} if settings in (None, "") else dict(to_kind(settings, "object"))
        except ValueError:
            raise ValueError(f"settings must be an object like {{\"text\": \"hi\"}}, not {settings!r}") from None
        changes.update({name: value for name, value in lines.items() if value not in (None, "")})
        if not changes:
            raise ValueError("Nothing to change: fill a line (Get settings gives them) or settings")
        await self._request("SetInputSettings", {"inputName": _source_name(source), "inputSettings": changes,
                                                 "overlay": True})
