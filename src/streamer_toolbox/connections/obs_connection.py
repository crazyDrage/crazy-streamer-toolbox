from pathlib import Path
from typing import Any, Callable

import simpleobsws
from nicegui import ui

from streamer_toolbox.connections.obs.boxes.get_current_scene import GetCurrentScene
from streamer_toolbox.connections.obs.boxes.switch_scene import SwitchScene
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.config.obs_config import ObsConfig
from streamer_toolbox.core.connections.connection_base import ConnectionBase
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.layout.box import Box
from streamer_toolbox.core.interfaces.video_probe import VideoProbe
from streamer_toolbox.connections.obs.lazy_obs_client import LazyObsClient
from streamer_toolbox.connections.obs.obs_connection_error import ObsConnectionError
from streamer_toolbox.connections.obs.obs_request_error import ObsRequestError
from streamer_toolbox.connections.obs.obs_audio_actions import ObsAudioActions
from streamer_toolbox.connections.obs.obs_filter_actions import ObsFilterActions
from streamer_toolbox.connections.obs.obs_fit_actions import add_fit_actions
from streamer_toolbox.connections.obs.obs_input_actions import ObsInputActions
from streamer_toolbox.connections.obs.obs_media_playback import ObsMediaPlayback
from streamer_toolbox.connections.obs.obs_new_source_actions import ObsNewSourceActions
from streamer_toolbox.connections.obs.obs_placement_actions import ObsPlacementActions
from streamer_toolbox.connections.obs.obs_output_actions import ObsOutputActions
from streamer_toolbox.connections.obs.obs_request_actions import ObsRequestActions
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.actions.json_boxes import JsonBoxes
from streamer_toolbox.core.values.value_kind import ValueKind
from streamer_toolbox.core.values.value_kinds import ValueKinds
from streamer_toolbox.connections.obs.obs_read_actions import ObsReadActions
from streamer_toolbox.connections.obs.obs_scene_actions import ObsSceneActions
from streamer_toolbox.connections.obs.obs_source_actions import ObsSourceActions
from streamer_toolbox.connections.obs.obs_status import ObsStatus
from streamer_toolbox.connections.obs.simpleobsws_connection_checker import SimpleobswsConnectionChecker
from streamer_toolbox.connections.obs.simpleobsws_scene_item_editor import SimpleobswsSceneItemEditor

JSON_BOXES = Path(__file__).with_name("obs") / "boxes"  # the boxes written as JSON (see JsonBoxes)


class ObsConnection(ConnectionBase):
    """OBS over obs-websocket v5. Stays connected; if OBS goes away, the next OBS action reconnects."""

    id = "obs"
    title = "OBS"
    icon = "videocam"
    retry_when_down = True

    def __init__(self, config: ObsConfig, probe: VideoProbe,
                 client_factory: Callable[[str, str], Any] = simpleobsws.WebSocketClient) -> None:
        super().__init__({"url": "ws://127.0.0.1:4455", "password": ""},
                         {"enabled": config.enabled, "url": config.url, "password": config.password})
        self._fit_targets = config.fit_targets
        self._probe = probe
        self._client_factory = client_factory
        self._checker = SimpleobswsConnectionChecker(client_factory)
        self._client: Any = None
        self._lazy: LazyObsClient | None = None

    def fields(self) -> list[SettingField]:
        return [SettingField("url", "Address", hint="OBS → Tools → WebSocket Server Settings → Show Connect Info"),
                SettingField("password", "Password", secret=True)]

    async def start(self) -> None:
        self._set_status(ConnectionStatus(ConnectionState.CONNECTING))
        self._client = self._client_factory(self._settings["url"], self._settings["password"])
        self._lazy = LazyObsClient(self._client)
        try:
            self._set_status(_connected(await self._checker.read(self._lazy)))
        except Exception as e:  # shown on the tab; OBS actions keep trying to reconnect
            self._set_status(ConnectionStatus(ConnectionState.ERROR, str(e)))

    async def stop(self) -> None:
        if self._client is not None and self._client.ws_open:
            await self._client.disconnect()
        self._client = self._lazy = None
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    async def keep_alive(self) -> None:
        if self.status.ok and (self._client is None or not self._client.ws_open):  # OBS was closed
            self._set_status(ConnectionStatus(ConnectionState.ERROR, "OBS closed the connection"))
        await super().keep_alive()

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        try:
            return _connected(await self._checker.check(settings["url"], settings["password"]))
        except Exception as e:
            return ConnectionStatus(ConnectionState.ERROR, str(e))

    async def call(self, request: simpleobsws.Request, timeout: int = 15) -> simpleobsws.RequestResponse:
        """For OBS actions. Reconnects if OBS was restarted or wasn't running when the toolbox started."""
        if not self._settings["enabled"]:
            raise NotConnectedError("OBS is switched off under Connections → OBS")
        if self._lazy is None:
            await self.start()
        try:
            response = await self._lazy.call(request, timeout)
        except ObsConnectionError as e:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, str(e)))
            raise
        if not self.status.ok:  # it came back: show the fresh facts
            self._set_status(_connected(await self._checker.read(self._lazy)))
        return response

    async def switch_scene(self, scene: str) -> None:
        response = await self.call(simpleobsws.Request("SetCurrentProgramScene", {"sceneName": scene}))
        if not response.ok():
            status = response.requestStatus
            raise ObsRequestError("SetCurrentProgramScene", status.code, status.comment)

    async def current_scene(self) -> str:
        response = await self.call(simpleobsws.Request("GetCurrentProgramScene"))
        if not response.ok():
            status = response.requestStatus
            raise ObsRequestError("GetCurrentProgramScene", status.code, status.comment)
        return response.responseData["currentProgramSceneName"]

    async def scene_names(self) -> list[str]:
        response = await self.call(simpleobsws.Request("GetSceneList"))
        if not response.ok():
            status = response.requestStatus
            raise ObsRequestError("GetSceneList", status.code, status.comment)
        return [scene["sceneName"] for scene in reversed(response.responseData["scenes"])]

    def add_actions(self, actions: ActionRegistry) -> None:
        add_fit_actions(actions, self._fit_targets, self._probe, SimpleobswsSceneItemEditor(self))
        ObsSourceActions(self.call).add_to(actions)
        requests = ObsRequests(self.call)
        # the boxes that are only a request with fields: obs/boxes/*.json
        kinds = ValueKinds([
            ValueKind("obs.scene", "OBS scene", extra="options", setting=requests.scene_names),
            ValueKind("obs.source", "OBS source", extra="options", setting=requests.input_names),
            ValueKind("obs.scene_item", "What sits in an OBS scene", extra="options",
                      setting=requests.source_names)])
        ObsRequestActions(self.call).add_to(actions)
        ObsInputActions(self.call).add_to(actions)
        for boxes in (ObsMediaPlayback(requests), ObsAudioActions(requests), ObsOutputActions(requests),
                      ObsFilterActions(requests), ObsNewSourceActions(requests), ObsPlacementActions(requests),
                      ObsSceneActions(requests), ObsReadActions(requests)):
            boxes.add_to(actions)
        JsonBoxes(JSON_BOXES, kinds).add_to(actions, "obs", requests)
        for box in (SwitchScene(self), GetCurrentScene(self)):
            actions.add_box(box, "obs")

    def add_gui_settings(self) -> None:
        if not self._fit_targets:
            return
        ui.label("Fit video to source").classes("text-sm font-semibold pt-2")
        for target in self._fit_targets:
            with ui.column().classes("w-full gap-0 border-t border-gray-500/30 pt-2"):
                ui.label(f"{target.source}  →  action obs.fit_{target.name}").classes("text-sm font-medium")
                for name, value in (("Scenes", ", ".join(target.scenes)), ("Landscape", _box(target.landscape)),
                                    ("Portrait", _box(target.portrait))):
                    with ui.row().classes("w-full no-wrap gap-3 text-sm"):
                        ui.label(name).classes("w-28 shrink-0 opacity-70")
                        ui.label(value)


def _connected(status: ObsStatus) -> ConnectionStatus:
    return ConnectionStatus(ConnectionState.CONNECTED, "", (
        ("OBS", f"{status.obs_version} (websocket {status.websocket_version})"),
        ("Profile", status.profile),
        ("Scene collection", status.scene_collection),
        ("Scenes", ", ".join(status.scenes) or "none"),
    ))


def _box(box: Box) -> str:
    return f"{box.width:g}×{box.height:g} at {box.x:g}, {box.y:g}"
