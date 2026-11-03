import asyncio
import uuid
from pathlib import PureWindowsPath
from typing import Any

from streamer_toolbox.connections.obs.boxes.media_status import MediaStatus
from streamer_toolbox.connections.obs.boxes.new_media_source import NewMediaSource
from streamer_toolbox.connections.obs.boxes.obs_audio_box import monitor_type, track_numbers, TRACKS
from streamer_toolbox.connections.obs.boxes.obs_media_playback_shared import (ADDRESS_STARTS, FINISHED, PLACE,
                                                                              STARTED, _seconds)
from streamer_toolbox.connections.obs.boxes.place_like_source import PlaceLikeSource
from streamer_toolbox.connections.obs.boxes.play_video_once import PlayVideoOnce
from streamer_toolbox.connections.obs.boxes.wait_until_media_is_over import WaitUntilMediaIsOver
from streamer_toolbox.connections.obs.obs_placement import ObsPlacement
from streamer_toolbox.connections.obs.obs_request_error import ObsRequestError
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.box_value import to_bool


class ObsMediaPlayback:
    """Play video once: a Media Source made just for one video, with its own sound settings (monitoring, tracks,
    volume, like in the Audio Mixer's Advanced Audio Properties), shown in a scene, removed again when the video
    is over. Nothing to set up in OBS first, and two videos at once don't fight over one source.

    The end is noticed by asking OBS the media state a few times a second (local, cheap), so a clip shorter than
    that is still caught: ENDED counts even when PLAYING was never seen."""

    def __init__(self, requests: ObsRequests, poll_seconds: float = 0.2, start_timeout: float = 10.0) -> None:
        self._requests = requests
        self._poll = poll_seconds
        self._start_timeout = start_timeout
        self._running: set[asyncio.Task] = set()

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (PlayVideoOnce(self), NewMediaSource(self), PlaceLikeSource(self), WaitUntilMediaIsOver(self),
                    MediaStatus(self)):
            actions.add_box(box, "obs")

    async def play_once(self, scene: str, file: str, monitoring: str = "monitor and output", tracks: Any = "",
                        volume: float = 1.0, place_like: str = "", wait: bool = True,
                        place: Any = "") -> dict[str, Any]:
        made = await self.new_media_source(scene, file)
        name = made["source"]
        try:
            await self._set_up(scene, name, made["item_id"], monitoring, tracks, volume, place_like, place)
            await self._requests("SetSceneItemEnabled", {"sceneName": scene, "sceneItemId": made["item_id"],
                                                         "sceneItemEnabled": True})
        except BaseException:
            await self._remove(name)
            raise
        if to_bool(wait):
            return await self._play_and_remove(name)
        task = asyncio.create_task(self._play_and_remove(name))
        self._running.add(task)
        task.add_done_callback(self._running.discard)
        return {"seconds": 0, "source": name}

    async def new_media_source(self, scene: str, file: str, name: str = "",
                               visible: bool = False) -> dict[str, Any]:
        if not str(file).strip():
            raise ValueError("which file? (file is empty)")
        file = str(file).strip()
        online = file.casefold().startswith(ADDRESS_STARTS)  # OBS plays it from the address, nothing is downloaded
        what = "video" if online else PureWindowsPath(file).stem
        name = str(name).strip() or f"toolbox {what} {uuid.uuid4().hex[:6]}"
        source = {"input": file, "is_local_file": False} if online else {"local_file": file, "is_local_file": True}
        made = await self._requests("CreateInput", {
            "sceneName": scene, "inputName": name, "inputKind": "ffmpeg_source",
            "sceneItemEnabled": to_bool(visible),
            "inputSettings": {**source, "looping": False, "restart_on_activate": True,
                              "close_when_inactive": True}})
        return {"source": name, "scene": scene, "item_id": made["sceneItemId"]}

    async def place_like(self, scene: str, source: str, like: str) -> None:
        await self._place_like(scene, await self._requests.scene_item_id(scene, source), like)

    async def wait_media_end(self, source: str) -> dict[str, Any]:
        return {"seconds": await self._until_over(source)}

    async def media_status(self, source: str) -> dict[str, Any]:
        status = await self._requests("GetMediaInputStatus", {"inputName": source})
        return {"state": str(status.get("mediaState", "")).removeprefix("OBS_MEDIA_STATE_").lower(),
                "seconds": _seconds(status.get("mediaDuration")), "position": _seconds(status.get("mediaCursor"))}

    async def _set_up(self, scene: str, name: str, item: int, monitoring: str, tracks: Any, volume: float,
                      place_like: str, place: Any = "") -> None:
        await self._requests("SetInputAudioMonitorType", {"inputName": name, "monitorType": monitor_type(monitoring)})
        if str(tracks).strip():
            on = track_numbers(tracks)
            await self._requests("SetInputAudioTracks", {"inputName": name,
                                                         "inputAudioTracks": {t: t in on for t in TRACKS}})
        if float(volume) != 1.0:
            await self._requests("SetInputVolume", {"inputName": name, "inputVolumeMul": max(float(volume), 0.0)})
        if place not in (None, ""):  # a place of its own wins over "like a source"
            await self._requests("SetSceneItemTransform", {
                "sceneName": scene, "sceneItemId": item,
                "sceneItemTransform": ObsPlacement.from_value(place).to_transform()})
        elif place_like:
            await self._place_like(scene, item, place_like)

    async def _place_like(self, scene: str, item: int, other: str) -> None:
        """Same spot, and fitted into the other source's box (its bounds, or the size it is shown at)."""
        other_id = await self._requests.scene_item_id(scene, other)
        now = (await self._requests("GetSceneItemTransform", {"sceneName": scene,
                                                              "sceneItemId": other_id}))["sceneItemTransform"]
        place = {k: now[k] for k in PLACE if k in now}
        has_bounds = now.get("boundsType", "OBS_BOUNDS_NONE") != "OBS_BOUNDS_NONE"
        place.update({"boundsType": now["boundsType"] if has_bounds else "OBS_BOUNDS_SCALE_INNER",
                      "boundsWidth": now["boundsWidth"] if has_bounds else now.get("width", 0),
                      "boundsHeight": now["boundsHeight"] if has_bounds else now.get("height", 0)})
        if place["boundsWidth"] <= 0 or place["boundsHeight"] <= 0:  # the other one has no size (sound only)
            for key in ("boundsType", "boundsWidth", "boundsHeight"):
                place.pop(key)
        await self._requests("SetSceneItemTransform", {"sceneName": scene, "sceneItemId": item,
                                                       "sceneItemTransform": place})

    async def _play_and_remove(self, name: str) -> dict[str, Any]:
        try:
            return {"seconds": await self._until_over(name), "source": name}
        finally:
            await self._remove(name)

    async def _until_over(self, name: str) -> float:
        loop = asyncio.get_running_loop()
        give_up = loop.time() + self._start_timeout
        started = False
        seconds = 0.0
        while True:
            try:
                status = await self._requests("GetMediaInputStatus", {"inputName": name})
            except ObsRequestError:  # removed by hand in OBS: over as well
                return seconds
            state = status.get("mediaState", "")
            seconds = _seconds(status.get("mediaDuration")) or seconds
            if state == "OBS_MEDIA_STATE_ERROR":
                raise RuntimeError(f"OBS couldn't play {name!r}: is the file there and a video or sound?")
            if state in FINISHED or (started and state == "OBS_MEDIA_STATE_STOPPED"):
                return seconds
            started = started or state in STARTED
            if not started and loop.time() > give_up:
                raise TimeoutError(f"the video didn't start within {self._start_timeout:g} s: is the scene live "
                                   "(a source only plays when its scene is shown) and the file right?")
            await asyncio.sleep(self._poll)

    async def _remove(self, name: str) -> None:
        try:
            await asyncio.shield(self._requests("RemoveInput", {"inputName": name}))
        except ObsRequestError:
            pass  # already gone


