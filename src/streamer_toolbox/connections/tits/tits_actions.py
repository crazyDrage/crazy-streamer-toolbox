from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry

Ask = Callable[[str, dict[str, Any] | None], Awaitable[dict[str, Any]]]  # message type, data → the answer's data


class TitsActions:
    """T.I.T.S.' boxes: throw an item at the model, activate a trigger. Items and triggers are picked by
    name (the picker lists them from the running program); the id is looked up."""

    def __init__(self, ask: Ask) -> None:
        self._ask = ask

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("tits.throw", self.throw, "Throws an item at the model", "Throw item",
                    options={"item": self.item_names}, outputs={"thrown": "number"},
                    hints={"amount": "How many", "delay": "Seconds between two throws, e.g. 0.05"})
        actions.add("tits.activate_trigger", self.activate_trigger, "Activates a trigger made in T.I.T.S.",
                    "Activate trigger", options={"trigger": self.trigger_names})

    async def item_names(self) -> list[str]:
        try:
            return sorted(await self._items())
        except ConnectionError:
            return []

    async def trigger_names(self) -> list[str]:
        try:
            return sorted(await self._triggers())
        except ConnectionError:
            return []

    async def throw(self, item: str, amount: int = 1, delay: float = 0.05) -> dict[str, int]:
        item_id = _find(await self._items(), item, "item")
        answer = await self._ask("TITSThrowItemsRequest", {
            "items": [item_id], "delayTime": max(float(delay), 0), "amountOfThrows": max(int(amount), 1),
            "errorOnMissingID": True})
        return {"thrown": int(answer.get("numberOfThrownItems") or 0)}

    async def activate_trigger(self, trigger: str) -> None:
        triggers = await self._triggers()
        trigger_id = _find(triggers, trigger, "trigger")
        name = next(n for n, i in triggers.items() if i == trigger_id)
        await self._ask("TITSTriggerActivateRequest", {"triggerID": trigger_id, "triggerName": name})

    async def _items(self) -> dict[str, str]:
        answer = await self._ask("TITSItemListRequest", {"sendImage": False})
        return _by_name(answer.get("items"))

    async def _triggers(self) -> dict[str, str]:
        return _by_name((await self._ask("TITSTriggerListRequest", None)).get("triggers"))


def _by_name(entries: Any) -> dict[str, str]:
    """name → id"""
    return {str(e.get("name") or e.get("ID")): str(e.get("ID") or "")
            for e in entries or [] if isinstance(e, dict)}


def _find(known: dict[str, str], name: str, what: str) -> str:
    wanted = str(name).strip()
    found = known.get(wanted) or next((i for n, i in known.items() if n.casefold() == wanted.casefold()), None)
    if found is None:
        raise KeyError(f"T.I.T.S. has no {what} named {wanted!r}")
    return found
