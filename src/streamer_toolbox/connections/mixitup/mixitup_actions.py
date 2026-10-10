from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import quote

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.box_value import to_bool

Send = Callable[..., Awaitable[Any]]  # (method, path, **httpx kwargs) → the answer
PLATFORMS = ["Twitch", "YouTube", "Trovo", "All"]
STATES = {"on": 1, "off": 0, "toggle": 2}


class MixItUpActions:
    """Every part of Mix It Up's Developer API v2 as boxes (mixitup.bot/docs/reference/developer-api): commands
    (run, on / off), chat (send, clear), a viewer (by platform + name) and their currency (rats), inventory items,
    counters. Names in, IDs looked up: a renamed command or currency needs no change in the flow."""

    def __init__(self, send: Send) -> None:
        self._send = send

    def add_to(self, actions: ActionRegistry) -> None:
        group = {"group": "Commands"}
        actions.add("mixitup.run_command", self.run_command, "Runs a Mix It Up command or action group by its name",
                    "Run Mix It Up command", options={"command": self.command_groups, "platform": _viewer_platforms},
                    labels={"ignore_requirements": "Ignore its requirements"},
                    hints={"arguments": "What follows the command, like typed after it in chat",
                           "ignore_requirements": "Runs even when its cooldown, cost or role says no"}, **group)
        actions.add("mixitup.set_command", self.set_command, "Switches a Mix It Up command on, off or the other way",
                    "Command on / off", options={"command": self.command_groups, "state": _states}, **group)
        actions.add("mixitup.send_chat", self.send_chat, "Sends a chat message through Mix It Up", "Send chat",
                    group="Chat", options={"platform": _platforms},
                    labels={"as_streamer": "As you (not the bot)"})
        actions.add("mixitup.clear_chat", self.clear_chat, "Clears the chat on every platform", "Clear chat",
                    group="Chat")
        users = {"group": "Viewers", "options": {"platform": _viewer_platforms}}
        actions.add("mixitup.get_user", self.get_user, "A viewer as Mix It Up knows them: id, name, watch minutes, "
                    "currencies and items by name", "Get viewer", outputs={"id": "text", "name": "text",
                                                                           "minutes": "number"}, **users)
        money = {"group": "Currency", "options": {"currency": self.currency_names, "platform": _viewer_platforms}}
        actions.add("mixitup.get_currency", self.get_currency, "How much of a currency (e.g. rats) a viewer has",
                    "Get currency", **money)
        actions.add("mixitup.add_currency", self.add_currency, "Gives a viewer some currency (a minus number takes "
                    "it away)", "Add currency", **money)
        actions.add("mixitup.set_currency", self.set_currency, "Sets a viewer's currency to an amount",
                    "Set currency", **money)
        items = {"group": "Inventory", "options": {"item": self.item_names, "platform": _viewer_platforms},
                 "hints": {"item": "inventory · item"}}
        actions.add("mixitup.get_item", self.get_item, "How many of an inventory item a viewer has", "Get item",
                    **items)
        actions.add("mixitup.add_item", self.add_item, "Gives a viewer items (a minus number takes them away)",
                    "Add item", **items)
        actions.add("mixitup.set_item", self.set_item, "Sets how many of an item a viewer has", "Set item", **items)
        counters = {"group": "Counters", "options": {"counter": self.counter_names}}
        actions.add("mixitup.get_counter", self.get_counter, "A Mix It Up counter's value", "Get counter",
                    **counters)
        actions.add("mixitup.add_to_counter", self.add_to_counter, "Adds to a counter (a minus number takes away)",
                    "Add to counter", **counters)
        actions.add("mixitup.set_counter", self.set_counter, "Sets a counter to a value (makes it if it's new)",
                    "Set counter", **counters)
        actions.add("mixitup.reset_counter", self.reset_counter, "Sets a counter back to 0", "Reset counter",
                    **counters)

    # ---- commands ----

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

    async def run_command(self, command: str, arguments: str = "", platform: str = "Twitch",
                          ignore_requirements: bool = False) -> None:
        body: dict[str, Any] = {"Arguments": str(arguments)}
        if platform and platform != "Twitch":
            body["Platform"] = platform
        if to_bool(ignore_requirements):
            body["IgnoreRequirements"] = True
        await self._send("POST", f"commands/{await self.command_id(command)}", json=body)

    async def set_command(self, command: str, state: str = "on") -> None:
        if state not in STATES:
            raise ValueError(f"state is on, off or toggle, not {state!r}")
        await self._send("PATCH", f"commands/{await self.command_id(command)}/state/{STATES[state]}")

    # ---- chat ----

    async def send_chat(self, message: str, platform: str = "All", as_streamer: bool = False) -> None:
        await self._send("POST", "chat/message", json={"Message": str(message), "Platform": platform or "All",
                                                       "SendAsStreamer": to_bool(as_streamer)})

    async def clear_chat(self) -> None:
        await self._send("POST", "chat/clear")

    # ---- viewers, currency, items ----

    async def _user(self, username: str, platform: str) -> dict[str, Any]:
        name = str(username).strip().lstrip("@")
        if not name:
            raise ValueError("which viewer? (username is empty)")
        answer = await self._send("GET", f"users/{platform or 'Twitch'}/{_part(name)}")
        user = answer.get("User", answer) if isinstance(answer, dict) else None  # the real one: {"User": {...}}
        if not isinstance(user, dict) or "ID" not in user:
            raise LookupError(f"Mix It Up doesn't know the viewer {name!r} on {platform}")
        return user

    async def get_user(self, username: str, platform: str = "Twitch") -> dict[str, Any]:
        user = await self._user(username, platform)
        data = (user.get("PlatformData") or {}).get(platform or "Twitch") or {}
        currencies = {c["ID"]: c["Name"] for c in await self._send("GET", "currency") or []}
        return {"id": user["ID"], "name": data.get("DisplayName") or data.get("Username") or str(username),
                "minutes": user.get("OnlineViewingMinutes", 0),
                "currency": {currencies.get(k, k): v for k, v in (user.get("CurrencyAmounts") or {}).items()},
                "items": user.get("InventoryAmounts") or {}}

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

    async def add_currency(self, currency: str, username: str, amount: int, platform: str = "Twitch") -> int:
        await self._money("PATCH", currency, username, platform, Amount=int(amount))
        return await self.get_currency(currency, username, platform)

    async def set_currency(self, currency: str, username: str, amount: int, platform: str = "Twitch") -> None:
        await self._money("PUT", currency, username, platform, Amount=int(amount))

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

    async def get_item(self, item: str, username: str, platform: str = "Twitch") -> int:
        return _amount(await self._send("GET", await self._item_path(item, username, platform)))

    async def add_item(self, item: str, username: str, amount: int = 1, platform: str = "Twitch") -> None:
        await self._send("PATCH", await self._item_path(item, username, platform), json={"Amount": int(amount)})

    async def set_item(self, item: str, username: str, amount: int, platform: str = "Twitch") -> None:
        await self._send("PUT", await self._item_path(item, username, platform), json={"Amount": int(amount)})

    # ---- counters ----

    async def counter_names(self) -> list[str]:
        return [c["Name"] for c in (await self._send("GET", "counters") or {}).get("Counters", [])]

    async def get_counter(self, counter: str) -> float:
        return _amount(await self._send("GET", f"counters/{_part(counter)}"))

    async def add_to_counter(self, counter: str, amount: float = 1) -> float:
        await self._send("POST", f"counters/{_part(counter)}/update", json={"Amount": float(amount)})
        return await self.get_counter(counter)

    async def set_counter(self, counter: str, amount: float) -> None:
        if counter not in await self.counter_names():
            await self._send("POST", "counters", json={"Name": counter})
        await self._send("POST", f"counters/{_part(counter)}/set", json={"Amount": float(amount)})

    async def reset_counter(self, counter: str) -> None:
        await self._send("POST", f"counters/{_part(counter)}/reset")


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
