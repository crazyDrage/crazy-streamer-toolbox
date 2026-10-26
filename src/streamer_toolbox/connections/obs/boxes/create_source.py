from typing import Any

from streamer_toolbox.connections.obs.boxes.obs_new_source_box import ObsNewSourceBox
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.data.box_value import to_bool, to_kind


class CreateSource(ObsNewSourceBox):
    name = "create_source"
    label = "Create source"
    help = 'Makes a new source in a scene, like OBS\'s + under Sources; settings = an object like {"file": ' \
           '"C:\\\\meme.png"} (Get source settings of one like it shows the names)'
    group = "Sources"
    hints = {"name": "must be new: OBS has no two sources with one name"}
    outputs = {"source": "text", "scene": "text", "item_id": "number"}

    def __init__(self, requests: ObsRequests) -> None:
        super().__init__(requests)
        self.options = {"scene": self._requests.scene_names, "kind": self.kind_names}

    async def run(self, scene: str, name: str, kind: str, settings: Any = "",
                  visible: bool = True) -> dict[str, Any]:
        if not str(name).strip():
            raise ValueError("the new source needs a name")
        try:
            values = to_kind(settings, "object") if settings not in (None, "") else {}
        except ValueError:
            raise ValueError(f"settings must be an object like {{\"file\": \"...\"}}, not {settings!r}") from None
        made = await self._requests("CreateInput", {"sceneName": scene, "inputName": str(name), "inputKind": kind,
                                                    "inputSettings": values, "sceneItemEnabled": to_bool(visible)})
        return {"source": str(name), "scene": scene, "item_id": made.get("sceneItemId")}
