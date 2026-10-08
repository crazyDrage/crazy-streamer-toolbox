from pathlib import Path
from typing import Any

from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.files.file_types import IMAGE_TYPES

RECORD = {"start": "StartRecord", "stop": "StopRecord", "toggle": "ToggleRecord", "pause": "PauseRecord",
          "resume": "ResumeRecord"}
STREAM = {"start": "StartStream", "stop": "StopStream", "toggle": "ToggleStream"}
REPLAY = {"save": "SaveReplayBuffer", "start": "StartReplayBuffer", "stop": "StopReplayBuffer",
          "toggle": "ToggleReplayBuffer"}
VIRTUAL_CAMERA = {"start": "StartVirtualCam", "stop": "StopVirtualCam", "toggle": "ToggleVirtualCam"}
IMAGE_FORMATS = {".png": "png", ".jpg": "jpg", ".jpeg": "jpg", ".bmp": "bmp", ".webp": "webp"}


class ObsOutputActions:
    """OBS boxes for what OBS sends out: recording, streaming, the replay buffer (save the last seconds as a
    clip), the virtual camera; a screenshot of a source or scene; OBS's own stats; and pressing one of OBS's
    hotkeys (anything set under Settings → Hotkeys, without a key)."""

    def __init__(self, requests: ObsRequests) -> None:
        self._requests = requests

    def add_to(self, actions: ActionRegistry) -> None:
        out = {"group": "Recording / streaming"}
        actions.add("obs.record", self.record, "Starts, stops, pauses or resumes recording; stop gives the file",
                    "Recording", options={"action": _choices(RECORD)}, **out)
        actions.add("obs.stream", self.stream, "Starts or stops the stream (careful: stop ends your stream)",
                    "Streaming", options={"action": _choices(STREAM)}, **out)
        actions.add("obs.replay_buffer", self.replay_buffer, "Saves the replay buffer as a clip (the last seconds "
                    "it keeps; set under Settings → Output → Replay Buffer), or starts / stops it",
                    "Replay buffer", options={"action": _choices(REPLAY)}, **out)
        actions.add("obs.virtual_camera", self.virtual_camera, "Starts or stops OBS's virtual camera",
                    "Virtual camera", options={"action": _choices(VIRTUAL_CAMERA)}, **out)
        actions.add("obs.get_output_status", self.output_status, "Whether you're live, recording, and for how long",
                    "Live / recording?", outputs={"streaming": "yes/no", "recording": "yes/no",
                                                  "stream_seconds": "number", "record_seconds": "number"},
                    live=True, **out)
        actions.add("obs.screenshot", self.screenshot, "Saves a picture of a source or scene as it is now (png, "
                    "jpg, bmp or webp, by the file's ending); gives the file", "Screenshot", group="Sources",
                    options={"source": self._source_and_scene_names},
                    hints={"width": "empty = its own size; the height follows"}, files={"file": IMAGE_TYPES})
        actions.add("obs.get_stats", self.stats, "OBS's numbers: CPU %, memory MB, FPS, dropped frames",
                    "OBS stats", group="Advanced", live=True,
                    outputs={"cpu": "number", "memory_mb": "number", "fps": "number",
                             "render_skipped": "number", "output_skipped": "number"})
        actions.add("obs.trigger_hotkey", self.trigger_hotkey, "Does what one of OBS's hotkeys does (Settings → "
                    "Hotkeys), without pressing a key", "OBS hotkey", group="Advanced",
                    options={"hotkey": self.hotkey_names})

    async def record(self, action: str = "toggle") -> str:
        answer = await self._requests(_request(RECORD, action))
        return answer.get("outputPath", "")

    async def stream(self, action: str = "toggle") -> None:
        await self._requests(_request(STREAM, action))

    async def replay_buffer(self, action: str = "save") -> None:
        await self._requests(_request(REPLAY, action))

    async def virtual_camera(self, action: str = "toggle") -> None:
        await self._requests(_request(VIRTUAL_CAMERA, action))

    async def output_status(self) -> dict[str, Any]:
        stream = await self._requests("GetStreamStatus")
        record = await self._requests("GetRecordStatus")
        return {"streaming": bool(stream.get("outputActive")), "recording": bool(record.get("outputActive")),
                "stream_seconds": round(stream.get("outputDuration", 0) / 1000),
                "record_seconds": round(record.get("outputDuration", 0) / 1000)}

    async def screenshot(self, source: str, file: str, width: int | None = None) -> str:
        path = Path(str(file)).expanduser()
        image_format = IMAGE_FORMATS.get(path.suffix.casefold())
        if image_format is None:
            raise ValueError(f"the file should end in {', '.join(IMAGE_FORMATS)}, not {path.name!r}")
        if not path.is_absolute():
            raise ValueError(f"OBS needs the full path (like C:\\clips\\shot.png), not {str(file)!r}")
        data: dict[str, Any] = {"sourceName": source, "imageFormat": image_format, "imageFilePath": str(path)}
        if width not in (None, ""):
            data["imageWidth"] = int(float(width))
        await self._requests("SaveSourceScreenshot", data)
        return str(path)

    async def stats(self) -> dict[str, float]:
        s = await self._requests("GetStats")
        return {"cpu": round(s.get("cpuUsage", 0), 1), "memory_mb": round(s.get("memoryUsage", 0)),
                "fps": round(s.get("activeFps", 0), 1), "render_skipped": s.get("renderSkippedFrames", 0),
                "output_skipped": s.get("outputSkippedFrames", 0)}

    async def trigger_hotkey(self, hotkey: str) -> None:
        await self._requests("TriggerHotkeyByName", {"hotkeyName": hotkey})

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
