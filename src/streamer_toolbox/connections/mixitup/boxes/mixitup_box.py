from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import quote

from streamer_toolbox.core.interfaces.box import Box


Send = Callable[..., Awaitable[Any]]
PLATFORMS = ["Twitch", "YouTube", "Trovo", "All"]
STATES = {"on": 1, "off": 0, "toggle": 2}


class MixitupBox(Box):
    """What the mixitup boxes share (not a box itself: it has no run).

    Every part of Mix It Up's Developer API v2 as boxes (mixitup.bot/docs/reference/developer-api): commands
    (run, on / off), chat (send, clear), a viewer (by platform + name) and their currency (rats), inventory items,
    counters. Names in, IDs looked up: a renamed command or currency needs no change in the flow."""

    def __init__(self, send: Send) -> None:
        self._send = send

    async def commands(self) -> list[dict[str, Any]]:
        return (await self._send("GET", "commands", params={"pageSize": 5000}) or {}).get("Commands", [])

    async def command_groups(self) -> dict[str, dict[str, str]]:
        """Type (Chat, Action Group, Twitch Channel Points, ...) → {name: name}: the field gets a type picker."""
        groups: dict[str, dict[str, str]] = {}
        for command in await self.commands():
            groups.setdefault(command.get("Type") or "Other", {})[command["Name"]] = command["Name"]
        return groups

    async def command_id(self, name: str) -> str:
        commands = await self.commands()
        found = next((c["ID"] for c in commands if c["Name"] == name), None) or \
            next((c["ID"] for c in commands if c["Name"].casefold() == str(name).casefold()), None)
        if found is None:
            raise LookupError(f"Mix It Up has no command named {name!r}")
        return found

    async def _user(self, username: str, platform: str) -> dict[str, Any]:
        name = str(username).strip().lstrip("@")
        if not name:
            raise ValueError("which viewer? (username is empty)")
        answer = await self._send("GET", f"users/{platform or 'Twitch'}/{_part(name)}")
        user = answer.get("User", answer) if isinstance(answer, dict) else None  # the real one: {"User": {...}}
        if not isinstance(user, dict) or "ID" not in user:
            raise LookupError(f"Mix It Up doesn't know the viewer {name!r} on {platform}")
        return user

    async def currency_names(self) -> list[str]:
        return [c["Name"] for c in await self._send("GET", "currency") or []]

    async def _currency_id(self, name: str) -> str:
        found = next((c["ID"] for c in await self._send("GET", "currency") or []
                      if c["Name"].casefold() == str(name).casefold()), None)
        if found is None:
            raise LookupError(f"Mix It Up has no currency named {name!r}")
        return found

    async def _money(self, method: str, currency: str, username: str, platform: str, **body: Any) -> Any:
        user = await self._user(username, platform)
        return await self._send(method, f"currency/{await self._currency_id(currency)}/{user['ID']}",
                                **({"json": body} if body else {}))

    async def get_currency(self, currency: str, username: str, platform: str = "Twitch") -> int:
        return _amount(await self._money("GET", currency, username, platform))

    async def _inventories(self) -> list[dict[str, Any]]:
        return await self._send("GET", "inventory") or []

    async def item_names(self) -> dict[str, dict[str, str]]:
        """inventory → {"inventory · item": item}: the field gets an inventory picker."""
        return {inv["Name"]: {f"{inv['Name']} · {item['Name']}": item["Name"] for item in inv.get("Items", [])}
                for inv in await self._inventories()}

    async def _item_path(self, item: str, username: str, platform: str) -> str:
        wanted_inventory, _, wanted_item = str(item).rpartition(" · ")
        for inventory in await self._inventories():
            if wanted_inventory and inventory["Name"] != wanted_inventory:
                continue
            for entry in inventory.get("Items", []):
                if entry["Name"].casefold() == wanted_item.casefold():
                    user = await self._user(username, platform)
                    return f"inventory/{inventory['ID']}/{entry['ID']}/{user['ID']}"
        raise LookupError(f"Mix It Up has no inventory item {item!r}")

    async def counter_names(self) -> list[str]:
        return [c["Name"] for c in (await self._send("GET", "counters") or {}).get("Counters", [])]

    async def get_counter(self, counter: str) -> float:
        return _amount(await self._send("GET", f"counters/{_part(counter)}"))


def _amount(answer: Any) -> Any:
    """Mix It Up answers an amount as a number or as {"Amount": n} (a counter: {"Name", "Amount"})."""
    if isinstance(answer, dict):
        for key in ("Amount", "Value", "amount"):
            if key in answer:
                return answer[key]
    return answer


async def _platforms() -> list[str]:
    return PLATFORMS


async def _viewer_platforms() -> list[str]:
    return [p for p in PLATFORMS if p != "All"]  # a viewer (or a command run for one) is on one platform


async def _states() -> list[str]:
    return list(STATES)


def _part(name: Any) -> str:
    """A name as one piece of the address (a counter called "a/b" or "#1" stays one piece)."""
    return quote(str(name), safe="")
