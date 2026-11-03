from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.interfaces.box import Box

Ask = Callable[[str, dict[str, Any] | None], Awaitable[dict[str, Any]]]
PICTURE = "data:image/png;base64,"


class TitsBox(Box):
    """What the tits boxes share (not a box itself: it has no run).

    T.I.T.S.' boxes, all its API has: throw items at the model, activate a trigger, and read what is there
    (the items, one item with its picture, the triggers). Items and triggers are picked by name (the pickers
    list them from the running program); the id is looked up."""

    def __init__(self, ask: Ask) -> None:
        self._ask = ask

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
