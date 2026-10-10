from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry

Ask = Callable[[str, dict[str, Any] | None], Awaitable[dict[str, Any]]]  # message type, data → the answer's data
PICTURE = "data:image/png;base64,"  # T.I.T.S. sends an item's picture as a PNG in base64: this in front makes
# it an address a web page (a widget, an overlay) can show as it is


class TitsActions:
    """T.I.T.S.' boxes, all its API has: throw items at the model, activate a trigger, and read what is there
    (the items, one item with its picture, the triggers). Items and triggers are picked by name (the pickers
    list them from the running program); the id is looked up."""

    def __init__(self, ask: Ask) -> None:
        self._ask = ask

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("tits.throw", self.throw, "Throws items at the model: one kind, or several kinds mixed "
                    "(T.I.T.S. picks among the ticked ones for each throw)", "Throw item",
                    many={"item": self.item_names}, outputs={"thrown": "number"},
                    hints={"item": "One item, or several (the list button): then each throw is one of them",
                           "amount": "How many throws in all", "delay": "Seconds between two throws, e.g. 0.05"})
        actions.add("tits.activate_trigger", self.activate_trigger, "Activates a trigger made in T.I.T.S.",
                    "Activate trigger", options={"trigger": self.trigger_names})
        actions.add("tits.get_items", self.items, "The items T.I.T.S. has now: their names and how many",
                    "Get T.I.T.S. items", live=True, outputs={"count": "number", "names": "list"})
        actions.add("tits.get_item", self.item, "One item of T.I.T.S. with its picture, e.g. to show what was "
                    "thrown in a widget (picture = an address a web page can show as it is)", "Get T.I.T.S. item",
                    options={"item": self.item_names},
                    outputs={"name": "text", "item_id": "text", "picture": "text"},
                    hints={"item": "Its name; wire the hit trigger's item into it"})
        actions.add("tits.get_triggers", self.triggers, "The triggers made in T.I.T.S.: their names and how many",
                    "Get T.I.T.S. triggers", live=True, outputs={"count": "number", "names": "list"})

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
        known = await self._items()
        names = [name for name in str(item if item is not None else "").split(",") if name.strip()] or [""]
        answer = await self._ask("TITSThrowItemsRequest", {
            "items": [_find(known, name, "item") for name in names], "delayTime": max(float(delay), 0),
            "amountOfThrows": max(int(amount), 1), "errorOnMissingID": True})
        return {"thrown": int(answer.get("numberOfThrownItems") or 0)}

    async def activate_trigger(self, trigger: str) -> None:
        triggers = await self._triggers()
        trigger_id = _find(triggers, trigger, "trigger")
        name = next(n for n, i in triggers.items() if i == trigger_id)
        await self._ask("TITSTriggerActivateRequest", {"triggerID": trigger_id, "triggerName": name})

    async def items(self) -> dict[str, Any]:
        names = sorted(await self._items(), key=str.casefold)
        return {"count": len(names), "names": names}

    async def item(self, item: str) -> dict[str, str]:
        item_id = _find(await self._items(), item, "item")
        answer = await self._ask("TITSItemInfoRequest", {"itemID": item_id, "sendImage": True})
        picture = str(answer.get("encodedImage") or "")
        return {"name": str(answer.get("name") or item).strip(), "item_id": item_id,
                "picture": PICTURE + picture if picture else ""}

    async def triggers(self) -> dict[str, Any]:
        names = sorted(await self._triggers(), key=str.casefold)
        return {"count": len(names), "names": names}

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
    if not wanted:
        raise ValueError(f"Which {what}? Pick one made in T.I.T.S.")
    found = known.get(wanted) or next((i for n, i in known.items() if n.casefold() == wanted.casefold()), None)
    if found is None:  # not a KeyError: its text would come out in quotes
        raise LookupError(f"T.I.T.S. has no {what} named {wanted!r}")
    return found
