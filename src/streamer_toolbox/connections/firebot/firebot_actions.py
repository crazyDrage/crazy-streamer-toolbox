import json
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import quote

from streamer_toolbox.core.actions.action_registry import ActionRegistry

Send = Callable[..., Awaitable[Any]]  # send(method, path, **httpx kwargs) → Firebot's answer
NOT_AN_OBJECT = 'The arguments must be an object like {"user": "ann"}'


class FirebotActions:
    """Firebot's boxes, over its local API (docs.firebot.app/v5/dev/api). What happens is built in Firebot
    as a preset effect list; the toolbox runs it by name (the picker lists them from the running program)
    and can hand it arguments. Custom variables and counters can be read and set."""

    def __init__(self, send: Send) -> None:
        self._send = send

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("firebot.run_preset", self.run_preset, "Runs a preset effect list made in Firebot",
                    "Run Firebot effect list", options={"preset": self.preset_names},
                    hints={"args": 'Optional: an object with the list\'s arguments, like {"user": "ann"}',
                           "user": "Optional: the viewer the effects are run for",
                           "wait": "Yes: the box waits until Firebot ran all effects"})
        actions.add("firebot.get_variable", self.get_variable, "The value of a Firebot custom variable",
                    "Get Firebot variable", group="Variables", outputs={"value": "text"})
        actions.add("firebot.set_variable", self.set_variable, "Sets a Firebot custom variable",
                    "Set Firebot variable", group="Variables",
                    hints={"seconds": "Optional: Firebot forgets it after this long (0 = never)"})
        actions.add("firebot.get_counter", self.get_counter, "The value of a Firebot counter",
                    "Get Firebot counter", group="Counters", options={"counter": self.counter_names},
                    outputs={"value": "number"})
        actions.add("firebot.set_counter", self.set_counter, "Sets a Firebot counter, or adds to it",
                    "Set Firebot counter", group="Counters", options={"counter": self.counter_names},
                    outputs={"value": "number"},
                    hints={"add": "Yes: the value is added (a minus takes away). No: the counter becomes it"})

    async def preset_names(self) -> list[str]:
        return sorted(await self._listed("effects/preset"))

    async def counter_names(self) -> list[str]:
        return sorted(await self._listed("counters"))

    async def run_preset(self, preset: str, args: Any = None, user: str = "", wait: bool = False) -> None:
        preset_id = _find(await self._by_name("effects/preset"), preset, "preset effect list")
        body = {"args": _object(args), **({"username": str(user)} if str(user).strip() else {})}
        await self._send("POST", f"effects/preset/{quote(preset_id)}" + ("" if wait else "/run"), json=body)

    async def get_variable(self, name: str) -> dict[str, Any]:
        answer = await self._send("GET", f"custom-variables/{quote(_named(name))}")
        return {"value": answer.get("data", "") if isinstance(answer, dict) else answer}

    async def set_variable(self, name: str, value: Any = "", seconds: float = 0) -> None:
        await self._send("POST", f"custom-variables/{quote(_named(name))}",
                         json={"data": value, "ttl": max(int(float(seconds)), 0)})

    async def get_counter(self, counter: str) -> dict[str, Any]:
        counter_id = _find(await self._by_name("counters"), counter, "counter")
        answer = await self._send("GET", f"counters/{quote(counter_id)}")
        return {"value": answer.get("value", 0) if isinstance(answer, dict) else 0}

    async def set_counter(self, counter: str, value: float = 1, add: bool = False) -> dict[str, Any]:
        counter_id = _find(await self._by_name("counters"), counter, "counter")
        answer = await self._send("POST", f"counters/{quote(counter_id)}",
                                  json={"value": _number(value), "override": not add})
        return {"value": answer.get("newValue", 0) if isinstance(answer, dict) else 0}

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
        raise KeyError(f"Firebot has no {what} named {wanted!r}")
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
