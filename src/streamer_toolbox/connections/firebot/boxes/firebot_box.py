import json
from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.interfaces.box import Box


Send = Callable[..., Awaitable[Any]]
NOT_AN_OBJECT = 'The arguments must be an object like {"user": "ann"}'


class FirebotBox(Box):
    """What the firebot boxes share (not a box itself: it has no run).

    Firebot's boxes, over its local API (docs.firebot.app/v5/dev/api). What happens is built in Firebot
    as a preset effect list; the toolbox runs it by name (the picker lists them from the running program)
    and can hand it arguments. Custom variables and counters can be read and set."""

    def __init__(self, send: Send) -> None:
        self._send = send

    async def preset_names(self) -> list[str]:
        return sorted(await self._listed("effects/preset"))

    async def counter_names(self) -> list[str]:
        return sorted(await self._listed("counters"))

    async def _listed(self, path: str) -> dict[str, str]:
        try:
            return await self._by_name(path)
        except ConnectionError:
            return {}

    async def _by_name(self, path: str) -> dict[str, str]:
        """name → id"""
        return {str(e.get("name") or e.get("id")): str(e.get("id") or "")
                for e in await self._send("GET", path) or [] if isinstance(e, dict)}


def _find(known: dict[str, str], name: str, what: str) -> str:
    wanted = str(name).strip()
    found = known.get(wanted) or next((i for n, i in known.items() if n.casefold() == wanted.casefold()), None)
    if found is None:
        raise LookupError(f"Firebot has no {what} named {wanted!r}")
    return found


def _named(name: str) -> str:
    name = str(name).strip()
    if not name:
        raise ValueError("Which variable?")
    return name


def _number(value: Any) -> float | int:
    number = float(value)
    return int(number) if number.is_integer() else number


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
