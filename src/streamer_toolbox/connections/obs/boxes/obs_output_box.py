from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.interfaces.box import Box


RECORD = {"start": "StartRecord", "stop": "StopRecord", "toggle": "ToggleRecord", "pause": "PauseRecord",
          "resume": "ResumeRecord"}
STREAM = {"start": "StartStream", "stop": "StopStream", "toggle": "ToggleStream"}
REPLAY = {"save": "SaveReplayBuffer", "start": "StartReplayBuffer", "stop": "StopReplayBuffer",
          "toggle": "ToggleReplayBuffer"}
VIRTUAL_CAMERA = {"start": "StartVirtualCam", "stop": "StopVirtualCam", "toggle": "ToggleVirtualCam"}
IMAGE_FORMATS = {".png": "png", ".jpg": "jpg", ".jpeg": "jpg", ".bmp": "bmp", ".webp": "webp"}


class ObsOutputBox(Box):
    """What the obs output boxes share (not a box itself: it has no run).

    OBS boxes for what OBS sends out: recording, streaming, the replay buffer (save the last seconds as a
    clip), the virtual camera; a screenshot of a source or scene; OBS's own stats; and pressing one of OBS's
    hotkeys (anything set under Settings → Hotkeys, without a key)."""

    def __init__(self, requests: ObsRequests) -> None:
        self._requests = requests

    async def hotkey_names(self) -> list[str]:
        return sorted((await self._requests("GetHotkeyList"))["hotkeys"], key=str.casefold)

    async def _source_and_scene_names(self) -> list[str]:
        return await self._requests.scene_names() + await self._requests.source_names()


def _request(requests: dict[str, str], action: str) -> str:
    if action not in requests:
        raise ValueError(f"action is one of {', '.join(requests)}, not {action!r}")
    return requests[action]


def _choices(requests: dict[str, str]):
    async def choices() -> list[str]:
        return list(requests)
    return choices
