from typing import Any

from streamer_toolbox.connections.obs.boxes.obs_input_box import ObsInputBox, Call, _source_name


class GetSourceSettings(ObsInputBox):
    name = "get_source_settings"
    label = "Get source settings"
    help = "A source's settings as an object: every setting its kind has (what its Properties window shows, e.g. " \
           "file, text, url), the ones left at their default too"
    group = "Sources"

    def __init__(self, call: Call) -> None:
        super().__init__(call)
        self.options = {"source": self.input_names}

    async def run(self, source: str) -> dict[str, Any]:
        """OBS keeps only what was changed on the source; the rest is its kind's defaults (his round 81: a Browser
        source and a Text source take different settings, and OBS ignores a wrong one quietly)."""
        answer = await self._request("GetInputSettings", {"inputName": _source_name(source)})
        settings = answer.get("inputSettings", {})
        if not answer.get("inputKind"):
            return settings
        defaults = await self._request("GetInputDefaultSettings", {"inputKind": answer["inputKind"]})
        return {**defaults.get("defaultInputSettings", {}), **settings}
