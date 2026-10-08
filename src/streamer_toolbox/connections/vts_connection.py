import asyncio
import logging
from pathlib import Path
from typing import Any, Callable

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_base import ConnectionBase
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.data.box_value import to_bool
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.interfaces.model_mover import ModelMover
from streamer_toolbox.connections.vtube_studio.vts_animation import VtsAnimation
from streamer_toolbox.connections.vtube_studio.vts_animation_player import VtsAnimationPlayer
from streamer_toolbox.connections.vtube_studio.vts_api_error import VtsApiError
from streamer_toolbox.connections.vtube_studio.vts_client import VtsClient
from streamer_toolbox.connections.vtube_studio.vts_expression_actions import VtsExpressionActions
from streamer_toolbox.connections.vtube_studio.vts_hotkey_actions import VtsHotkeyActions
from streamer_toolbox.connections.vtube_studio.vts_item_actions import CLICKED, VtsItemActions
from streamer_toolbox.connections.vtube_studio.vts_look_actions import VtsLookActions
from streamer_toolbox.connections.vtube_studio.vts_position import VtsPosition
from streamer_toolbox.connections.vtube_studio.vts_position_store import VtsPositionStore

PLUGIN = {"pluginName": "streamer-toolbox", "pluginDeveloper": "crazyDrage"}
USER_DENIED = 50
MODEL_LOADED = "vts.model_loaded"  # event: {model} when VTube Studio finished loading a model
# VTS event → (toolbox event, its data from VTS's data); MODEL_LOADED is handled on its own (only when loaded)
EVENTS = {
    "TrackingStatusChangedEvent": ("vts.tracking", lambda d: {
        "face": bool(d.get("faceFound")), "left_hand": bool(d.get("leftHandFound")),
        "right_hand": bool(d.get("rightHandFound"))}),
    "BackgroundChangedEvent": ("vts.background", lambda d: {"background": d.get("backgroundName", "")}),
    "HotkeyTriggeredEvent": ("vts.hotkey", lambda d: {
        "hotkey": d.get("hotkeyName", ""), "hotkey_id": d.get("hotkeyID", ""), "action": d.get("hotkeyAction", ""),
        "by_toolbox": bool(d.get("hotkeyTriggeredByAPI")), "model": d.get("modelName", "")}),
    "ModelConfigChangedEvent": ("vts.model_config", lambda d: {
        "model": d.get("modelName", ""), "hotkeys_changed": bool(d.get("hotkeyConfigChanged"))}),
    "ModelMovedEvent": ("vts.model_moved", lambda d: {
        "model": d.get("modelName", ""),
        **VtsPosition.from_api(d.get("modelPosition") or {"positionX": 0, "positionY": 0, "rotation": 0,
                                                            "size": 0}).to_dict()}),
}
log = logging.getLogger(__name__)


class VtsConnection(ConnectionBase, ModelMover):
    """VTube Studio as a plugin: move the model (also to saved positions per model), trigger hotkeys.
    Its tab only holds the connection; positions and hotkeys are picked and saved in the flow editor.

    Pairing: only the Connect button asks VTube Studio for a token (VTS shows a popup the streamer must allow
    once); starting the toolbox never pops that up. The token is kept in its own file next to the settings.
    """

    id = "vtube_studio"
    title = "VTube Studio"
    icon = "face"
    retry_when_down = True  # VTS started after the toolbox gets connected by itself (token only, no popup)

    def __init__(self, settings: dict[str, Any], token_path: Path, positions: VtsPositionStore,
                 client_factory: Callable[[str], Any] = VtsClient, token_timeout: float = 120,
                 events: EventBus | None = None) -> None:
        super().__init__({"url": "ws://127.0.0.1:8001"}, settings)
        self._token_path = token_path
        self._positions = positions
        self._client_factory = client_factory
        self._token_timeout = token_timeout
        self._events = events
        self._client: Any = None
        self._items = VtsItemActions(self._request)
        self._animation: tuple[asyncio.Task, VtsAnimationPlayer] | None = None  # the one playing (one at a time)

    def fields(self) -> list[SettingField]:
        return [SettingField("url", "Address", hint="VTube Studio → Settings → Start API (port 8001)")]

    async def start(self) -> None:
        self._set_status(ConnectionStatus(ConnectionState.CONNECTING))
        try:
            self._client = await self._open(self._settings["url"], may_ask=False)
            await self._listen(self._client)
            self._set_status(await self._connected(self._client))
        except Exception as e:  # shown on the tab; actions try again
            await self._close()
            self._set_status(ConnectionStatus(ConnectionState.ERROR, _reason(e)))

    async def stop(self) -> None:
        await self.stop_animation()
        await self._close()
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    async def keep_alive(self) -> None:
        if self.status.ok and (self._client is None or not self._client.is_open):  # VTS was closed
            await self._close()
            self._set_status(ConnectionStatus(ConnectionState.ERROR, "VTube Studio closed the connection"))
        await super().keep_alive()

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        client = None
        try:
            client = await self._open(settings["url"], may_ask=True)
            return await self._connected(client)
        except Exception as e:
            return ConnectionStatus(ConnectionState.ERROR, _reason(e))
        finally:
            if client is not None:
                await client.close()

    # ---- what actions use ----

    async def current_model(self) -> tuple[str, VtsPosition]:
        data = await self._request("CurrentModelRequest")
        if not data.get("modelLoaded"):
            raise NotConnectedError("VTube Studio has no model loaded")
        return data["modelName"], VtsPosition.from_api(data["modelPosition"])

    async def position(self) -> VtsPosition:
        return (await self.current_model())[1]

    async def move(self, position: VtsPosition, seconds: float = 1.0) -> None:
        await self._request("MoveModelRequest", {"timeInSeconds": seconds, "valuesAreRelativeToModel": False,
                                                 **position.to_api()})

    async def play_animation(self, animation: VtsAnimation, repeat: int = 1, back_to_start: bool = False,
                             back_seconds: float = 1.0, forever: bool = False) -> None:
        """Plays it and returns when it's done (or stopped by stop_animation / a newer animation). forever: starts
        it in the background and returns at once; it loops until stopped."""
        await self.stop_animation()
        player = VtsAnimationPlayer(self)
        task = asyncio.create_task(player.play(animation, repeat, back_to_start, back_seconds, forever))
        self._animation = (task, player)
        task.add_done_callback(lambda done: self._animation_ended(done))
        if forever:
            while player.start is None and not task.done():  # it read the start spot: a stop can go back there
                await asyncio.sleep(0.01)
            if task.done() and not task.cancelled() and task.exception():
                raise task.exception()
            return
        await asyncio.wait({task})  # a stop cancels the animation, not the flow waiting here
        if not task.cancelled():
            task.result()  # its error, if any

    async def stop_animation(self, back_to_start: bool = False, back_seconds: float = 1.0) -> bool:
        """Stops the animation that's playing (a loop too); back_to_start: then to where it began. False if none
        was playing."""
        if self._animation is None:
            return False
        task, player = self._animation
        self._animation = None
        task.cancel()
        await asyncio.wait({task})
        if back_to_start:
            await player.go_back(back_seconds)
        return True

    def _animation_ended(self, task: asyncio.Task) -> None:
        if self._animation and self._animation[0] is task:
            self._animation = None
        if not task.cancelled() and task.exception():
            log.warning("model animation stopped: %s", task.exception())

    async def move_by(self, x: float = 0.0, y: float = 0.0, rotation: float = 0.0, size: float = 0.0,
                      seconds: float = 1.0) -> None:
        """Moves the model from where it is now: VTS adds these to its current x, y, rotation and size (empty = 0)."""
        await self._request("MoveModelRequest", {"timeInSeconds": float(seconds), "valuesAreRelativeToModel": True,
                                                 **VtsPosition(*(float(v or 0) for v in (x, y, rotation, size)))
                                                 .to_api()})

    async def move_some(self, x: float | None = None, y: float | None = None, rotation: float | None = None,
                        size: float | None = None, seconds: float = 1.0) -> None:
        """Moves the model to these values; the ones left empty stay as they are now."""
        given = {k: v for k, v in {"x": x, "y": y, "rotation": rotation, "size": size}.items() if v not in (None, "")}
        if len(given) < 4:
            given = {**(await self.current_model())[1].to_dict(), **given}
        await self.move(VtsPosition.from_dict(given), float(seconds))

    async def move_to_position(self, position: str, seconds: float = 1.0) -> dict[str, Any]:
        model, _ = await self.current_model()
        saved = self._positions.get(model, position)
        if saved is None:
            raise KeyError(f"no saved position {position!r} for model {model!r}")
        await self.move(saved, seconds)
        return {"model": model, "position": position}

    async def save_position(self, position: str) -> dict[str, Any]:
        model, current = await self.current_model()
        self._positions.save(model, position, current)
        return {"model": model, "position": position, **current.to_api()}

    async def position_names(self) -> list[str]:
        """Saved positions of the loaded model (for the flow editor)."""
        model, _ = await self.current_model()
        return self._positions.names(model)

    async def model_names(self) -> list[str]:
        return [m["modelName"] for m in (await self._request("AvailableModelsRequest")).get("availableModels", [])]

    async def load_model(self, model: str, wait_until_loaded: bool = True, seconds: float = 20.0) -> None:
        """model = its name as VTube Studio shows it, or its ID. wait_until_loaded: returns only once VTS reports
        the new model (the boxes after it act on that one), TimeoutError after seconds."""
        models = (await self._request("AvailableModelsRequest")).get("availableModels", [])
        found = next((m for m in models if model in (m["modelName"], m["modelID"])), None)
        if found is None:
            raise KeyError(f"VTube Studio has no model {model!r}")
        await self._request("ModelLoadRequest", {"modelID": found["modelID"]})
        if to_bool(wait_until_loaded):
            await self._wait_for_model(found["modelName"], float(seconds))

    async def _wait_for_model(self, name: str, seconds: float) -> None:
        for _ in range(max(1, int(seconds / 0.25))):
            await asyncio.sleep(0.25)
            try:
                if (await self.current_model())[0] == name:
                    return
            except NotConnectedError:  # no model while the new one loads
                pass
        raise TimeoutError(f"VTube Studio didn't load {name!r} within {seconds:g} s")

    async def ensure_model(self, model: str, wait: float = 10.0) -> None:
        """Loads the model unless it's the loaded one, and waits until VTS reports it."""
        if (await self.current_model())[0] == model:
            return
        await self.load_model(model, True, wait)

    def add_actions(self, actions: ActionRegistry) -> None:
        async def move_model_to(position: dict, seconds: float = 1.0, load_model: bool = False) -> None:
            model = position.get("model") if isinstance(position, dict) else None
            if to_bool(load_model) and model:
                await self.ensure_model(model)
            await self.move(VtsPosition.from_dict(position), seconds)

        async def get_model_position() -> dict[str, Any]:
            model, position = await self.current_model()
            return {**position.to_dict(), "model": model}

        async def play_animation(animation: dict, repeat: int = 1, loop_forever: bool = False,
                                 back_to_start: bool = False, back_seconds: float = 1.0) -> None:
            await self.play_animation(VtsAnimation.from_dict(animation), int(repeat), to_bool(back_to_start),
                                      float(back_seconds), to_bool(loop_forever))

        async def stop_animation(back_to_start: bool = False, back_seconds: float = 1.0) -> bool:
            return await self.stop_animation(to_bool(back_to_start), float(back_seconds))

        async def get_model() -> str:
            return (await self.current_model())[0]

        actions.add("vts.get_model_position", get_model_position,
                    "Reads where the model is now and which model it is: {x, y, rotation, size, model}. Save it in "
                    "a variable to use it later", "Get model position", group="Model position",
                    live=True, outputs={"x": "number", "y": "number", "rotation": "number", "size": "number",
                                        "model": "text"})
        actions.add("vts.move_model_to", move_model_to,
                    "Moves the model to a position, e.g. a variable made by Get model position. load_model: if the "
                    "position belongs to another model, load that model first",
                    "Move model to position", group="Model position",
                    capture="vts.get_model_position:position")
        actions.add("vts.move_model", self.move_some, "Moves the model to exact values; the ones left empty stay "
                    "as they are now (e.g. only x = only sideways)", "Move model (numbers)", group="Model position")
        actions.add("vts.move_model_by", self.move_by,
                    "Moves the model from where it is now, e.g. x -0.2 = a bit to the left (the screen is -1 to 1 "
                    "wide). 0 = keep that one", "Move model by (from where it is)", group="Model position")
        actions.add("vts.play_animation", play_animation,
                    "Plays a model animation: the model goes from spot to spot, each step taking its own time. "
                    "The steps are kept in this box (Edit: record them by moving the model in VTS); the box "
                    "ends when the animation is done. A new animation stops the one playing",
                    "Play model animation", group="Model position", editors={"animation": "vts_animation"},
                    labels={"back_to_start": "Back to the start", "back_seconds": "Seconds to go back"},
                    hints={"repeat": "Play it this many times in a row",
                           "loop_forever": "Keeps playing in the background until a Stop model animation box (or "
                                           "another animation) stops it. The flow goes on at once",
                           "back_to_start": "At the end, go back to where the model was when it started"})
        actions.add("vts.stop_animation", stop_animation,
                    "Stops the model animation that's playing (also one that loops forever). Gives true if one "
                    "was playing", "Stop model animation", group="Model position",
                    labels={"back_to_start": "Back to the start", "back_seconds": "Seconds to go back"},
                    hints={"back_to_start": "Then go back to where the model was when that animation began"})
        actions.add("vts.move_to_position", self.move_to_position,
                    "Moves the loaded model to one of its saved positions (old way; variables replace it)",
                    "Move model to saved position", group="Model position",
                    options={"position": self.position_names}, capture="vts.save_position")
        actions.add("vts.save_position", self.save_position,
                    "Saves where the loaded model is now under a name (old way; variables replace it)",
                    "Save model position", group="Model position", options={"position": self.position_names})
        actions.add("vts.get_model", get_model, "The name of the loaded model", "Get loaded model",
                    group="Model", live=True)
        actions.add("vts.load_model", self.load_model, "Loads a model by name", "Load model", group="Model",
                    options={"model": self.model_names},
                    labels={"wait_until_loaded": "Wait until it's loaded", "seconds": "Give up after (s)"},
                    hints={"wait_until_loaded": "On: the box ends when VTube Studio shows the new model, so the "
                                                "next boxes (e.g. move it) work on that one"})
        VtsHotkeyActions(self._request).add_to(actions)
        self._items.add_to(actions)
        VtsExpressionActions(self._request).add_to(actions)
        VtsLookActions(self._request).add_to(actions)

    # ---- internals ----

    async def _listen(self, client: Any) -> None:
        """VTS events go out on the EventBus as flow triggers: model loaded, tracking found / lost, background
        changed, hotkey fired, model config changed, model moved. Also catches the click Record pin spot waits for."""
        client.on_event = self._vts_event
        if self._events is None:
            return
        for name in ("ModelLoadedEvent", *EVENTS):
            await client.request("EventSubscriptionRequest", {"eventName": name, "subscribe": True, "config": {}})

    def _vts_event(self, kind: str, data: dict[str, Any]) -> None:
        if kind == CLICKED:
            self._items.clicked(data)
            return
        if self._events is None:
            return
        if kind == "ModelLoadedEvent" and data.get("modelLoaded"):
            self._events.publish(MODEL_LOADED, {"model": data.get("modelName", ""), "model_id": data.get("modelID")})
        elif kind in EVENTS:
            name, fields = EVENTS[kind]
            self._events.publish(name, fields(data))

    async def _request(self, message_type: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self._settings["enabled"]:
            raise NotConnectedError("VTube Studio is switched off under Connections → VTube Studio")
        if self._client is None or not self._client.is_open:
            await self.start()
            if not self.status.ok:
                raise NotConnectedError(f"VTube Studio: {self.status.detail}")
        return await self._client.request(message_type, data)

    async def _open(self, url: str, may_ask: bool) -> Any:
        client = self._client_factory(url)
        await client.connect()
        try:
            await self._authenticate(client, may_ask)
        except Exception:
            await client.close()
            raise
        return client

    async def _authenticate(self, client: Any, may_ask: bool) -> None:
        token = self._token_path.read_text(encoding="utf-8").strip() if self._token_path.exists() else ""
        if token:
            answer = await client.request("AuthenticationRequest", {**PLUGIN, "authenticationToken": token})
            if answer.get("authenticated"):
                return
            log.info("VTS token no longer valid (%s)", answer.get("reason"))
        if not may_ask:
            raise PermissionError("Not paired with VTube Studio yet: press Connect, then click Allow in VTS")
        self._set_status(ConnectionStatus(ConnectionState.CONNECTING, "Click Allow in VTube Studio"))
        token = (await client.request("AuthenticationTokenRequest", PLUGIN,
                                      timeout=self._token_timeout))["authenticationToken"]
        self._token_path.parent.mkdir(parents=True, exist_ok=True)
        self._token_path.write_text(token, encoding="utf-8")
        answer = await client.request("AuthenticationRequest", {**PLUGIN, "authenticationToken": token})
        if not answer.get("authenticated"):
            raise PermissionError(f"VTube Studio refused the token: {answer.get('reason', '')}")

    async def _connected(self, client: Any) -> ConnectionStatus:
        state = await client.request("APIStateRequest")
        model = await client.request("CurrentModelRequest")
        return ConnectionStatus(ConnectionState.CONNECTED, "", (
            ("VTube Studio", state.get("vTubeStudioVersion", "?")),
            ("Model", model.get("modelName", "none") if model.get("modelLoaded") else "none loaded"),
        ))

    async def _close(self) -> None:
        if self._client is not None:
            await self._client.close()
        self._client = None


def _reason(e: Exception) -> str:
    if isinstance(e, VtsApiError) and e.error_id == USER_DENIED:
        return "You clicked Deny in VTube Studio. Press Connect to be asked again."
    if isinstance(e, PermissionError):  # not paired / token refused; it's an OSError too, so check first
        return str(e)
    if isinstance(e, OSError):
        return "can't reach VTube Studio: is it running, with the API on (Settings → Start API)?"
    if isinstance(e, TimeoutError):
        return "VTube Studio didn't answer in time (was the Allow popup missed?)"
    return str(e) or type(e).__name__


