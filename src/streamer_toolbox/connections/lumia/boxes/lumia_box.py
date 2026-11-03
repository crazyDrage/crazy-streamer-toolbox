import json
from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.interfaces.box import Box

Send = Callable[[dict[str, Any]], Awaitable[None]]
Retrieve = Callable[[], Awaitable[dict[str, Any]]]
NOT_AN_OBJECT = 'The values must be an object like {"username": "ann"}'


class LumiaBox(Box):
    """What the lumia boxes share (not a box itself: it has no run).

    Lumia Stream's boxes, all through its Send API (dev.lumiastream.com): run one of its commands or
    alerts by name (the pickers list them from the running program), or set the lights to a colour.
    "Send to Lumia" is for the kinds without a box of their own (studio-scene, tts, ...): Lumia's docs name
    the kind and a value, which is what it sends."""

    def __init__(self, send: Send, retrieve: Retrieve) -> None:
        self._send = send
        self._retrieve = retrieve

    async def command_names(self) -> list[str]:
        return await self._listed("chat-command")

    async def alert_names(self) -> list[str]:
        return await self._listed("alert")

    async def kinds(self) -> list[str]:
        try:
            return [str(kind) for kind in (await self._retrieve()).get("types") or []]
        except ConnectionError:
            return []

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
