from typing import Any

from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.box_value import to_bool, to_kind

# OBS's names for the kinds of source → what its Add menu calls them (others are shown by their own name)
KIND_LABELS = {"ffmpeg_source": "Media Source", "image_source": "Image", "browser_source": "Browser",
               "text_gdiplus_v3": "Text (GDI+)", "text_gdiplus_v2": "Text (GDI+)", "color_source_v3": "Color Source",
               "vlc_source": "VLC Video Source", "slideshow_v2": "Image Slide Show", "slideshow": "Image Slide Show",
               "wasapi_input_capture": "Audio Input Capture", "wasapi_output_capture": "Audio Output Capture",
               "wasapi_process_output_capture": "Application Audio Capture", "dshow_input": "Video Capture Device",
               "window_capture": "Window Capture", "game_capture": "Game Capture",
               "monitor_capture": "Display Capture"}


class ObsNewSourceActions:
    """OBS boxes that make a new source in a scene (any kind, with its settings) and remove a source from OBS."""

    def __init__(self, requests: ObsRequests) -> None:
        self._requests = requests

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("obs.create_source", self.create_source, "Makes a new source in a scene, like OBS's + under "
                    "Sources; settings = an object like {\"file\": \"C:\\\\meme.png\"} (Get source settings of one "
                    "like it shows the names)", "Create source", group="Sources",
                    options={"scene": self._requests.scene_names, "kind": self.kind_names},
                    hints={"name": "must be new: OBS has no two sources with one name"},
                    outputs={"source": "text", "scene": "text", "item_id": "number"})
        actions.add("obs.remove_source", self.remove_source, "Removes a source from OBS: from every scene, with "
                    "its settings and filters (like Remove in OBS; it can't be undone)", "Remove source",
                    group="Sources", options={"source": self._requests.input_names})

    async def create_source(self, scene: str, name: str, kind: str, settings: Any = "",
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

    async def remove_source(self, source: str) -> None:
        await self._requests("RemoveInput", {"inputName": source})

    async def kind_names(self) -> dict[str, str]:
        kinds = (await self._requests("GetInputKindList", {"unversioned": False}))["inputKinds"]
        return dict(sorted(((k, KIND_LABELS.get(k, k)) for k in kinds), key=lambda pair: pair[1].casefold()))
