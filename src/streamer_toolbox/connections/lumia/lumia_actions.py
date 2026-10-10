import json
from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry

Send = Callable[[dict[str, Any]], Awaitable[None]]        # one {"type", "params"} → Lumia's Send API
Retrieve = Callable[[], Awaitable[dict[str, Any]]]        # Lumia's settings: types, options, lights
NOT_AN_OBJECT = 'The values must be an object like {"username": "ann"}'


class LumiaActions:
    """Lumia Stream's boxes, all through its Send API (dev.lumiastream.com): run one of its commands or
    alerts by name (the pickers list them from the running program), or set the lights to a colour.
    "Send to Lumia" is for the kinds without a box of their own (studio-scene, tts, ...): Lumia's docs name
    the kind and a value, which is what it sends."""

    def __init__(self, send: Send, retrieve: Retrieve) -> None:
        self._send = send
        self._retrieve = retrieve

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("lumia.command", self.command, "Runs one of Lumia Stream's commands, as if a viewer had "
                    "typed it", "Run Lumia command", options={"command": self.command_names},
                    hints={"hold": "Yes: the lights stay like this (it becomes the default state)"})
        actions.add("lumia.alert", self.alert, "Fires one of Lumia Stream's alerts", "Fire Lumia alert",
                    options={"alert": self.alert_names},
                    hints={"values": 'Optional: what the alert may show, like {"username": "ann", "bits": 100}'})
        actions.add("lumia.color", self.color, "Sets the lights to a colour for some seconds",
                    "Set Lumia lights", hints={
                        "color": "Like #FF4076", "brightness": "0 to 100", "seconds": "How long it stays",
                        "fade": "Seconds the change takes", "hold": "Yes: the lights stay like this"})
        actions.add("lumia.send", self.send, "Sends any other kind of thing Lumia Stream knows (a studio "
                    "scene, text to speech, ...)", "Send to Lumia", options={"kind": self.kinds},
                    hints={"value": "What that kind wants: a scene's name, the text to speak, ...",
                           "values": "Optional: more settings for it, as an object"})

    async def command_names(self) -> list[str]:
        return await self._listed("chat-command")

    async def alert_names(self) -> list[str]:
        return await self._listed("alert")

    async def kinds(self) -> list[str]:
        try:
            return [str(kind) for kind in (await self._retrieve()).get("types") or []]
        except ConnectionError:
            return []

    async def command(self, command: str, hold: bool = False) -> None:
        await self._send({"type": "chat-command", "params": {"value": _named(command, "command"),
                                                              **({"hold": True} if hold else {})}})

    async def alert(self, alert: str, values: Any = None) -> None:
        params: dict[str, Any] = {"value": _named(alert, "alert")}
        if _object(values):
            params["extraSettings"] = _object(values)
        await self._send({"type": "alert", "params": params})

    async def color(self, color: str = "#FF4076", brightness: float = 100, seconds: float = 4,
                    fade: float = 0, hold: bool = False) -> None:
        color = str(color).strip()
        if not (color.startswith("#") and len(color) == 7):
            raise ValueError("The colour must look like #FF4076")
        await self._send({"type": "hex-color", "params": {
            "value": color, "brightness": min(max(float(brightness), 0), 100),
            "transition": int(max(float(fade), 0) * 1000), "duration": int(max(float(seconds), 0) * 1000),
            **({"hold": True} if hold else {})}})

    async def send(self, kind: str, value: str = "", values: Any = None) -> None:
        await self._send({"type": _named(kind, "kind"), "params": {"value": value, **_object(values)}})

    async def _listed(self, kind: str) -> list[str]:
        try:
            options = (await self._retrieve()).get("options")
        except ConnectionError:
            return []
        entry = options.get(kind) if isinstance(options, dict) else None
        return sorted(set(_names(entry.get("values") if isinstance(entry, dict) else entry)))


def _names(values: Any) -> list[str]:
    """Every name in Lumia's list of values, which is flat for commands and grouped by platform for alerts."""
    if isinstance(values, str):
        return [values]
    if isinstance(values, dict):
        values = list(values.values())
    return [name for value in values or [] for name in _names(value)] if isinstance(values, list) else []


def _named(name: str, what: str) -> str:
    name = str(name).strip()
    if not name:
        raise ValueError(f"Which {what}?")
    return name


def _object(values: Any) -> dict[str, Any]:
    if values in (None, ""):
        return {}
    if isinstance(values, str):
        try:
            values = json.loads(values)
        except ValueError:
            raise ValueError(NOT_AN_OBJECT) from None
    if not isinstance(values, dict):
        raise ValueError(NOT_AN_OBJECT)
    return dict(values)
