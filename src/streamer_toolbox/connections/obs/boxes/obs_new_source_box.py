from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.interfaces.box import Box


KIND_LABELS = {"ffmpeg_source": "Media Source", "image_source": "Image", "browser_source": "Browser",
               "text_gdiplus_v3": "Text (GDI+)", "text_gdiplus_v2": "Text (GDI+)", "color_source_v3": "Color Source",
               "vlc_source": "VLC Video Source", "slideshow_v2": "Image Slide Show", "slideshow": "Image Slide Show",
               "wasapi_input_capture": "Audio Input Capture", "wasapi_output_capture": "Audio Output Capture",
               "wasapi_process_output_capture": "Application Audio Capture", "dshow_input": "Video Capture Device",
               "window_capture": "Window Capture", "game_capture": "Game Capture",
               "monitor_capture": "Display Capture"}


class ObsNewSourceBox(Box):
    """What the obs new source boxes share (not a box itself: it has no run).

    OBS boxes that make a new source in a scene (any kind, with its settings) and remove a source from OBS."""

    def __init__(self, requests: ObsRequests) -> None:
        self._requests = requests

    async def kind_names(self) -> dict[str, str]:
        kinds = (await self._requests("GetInputKindList", {"unversioned": False}))["inputKinds"]
        return dict(sorted(((k, KIND_LABELS.get(k, k)) for k in kinds), key=lambda pair: pair[1].casefold()))
