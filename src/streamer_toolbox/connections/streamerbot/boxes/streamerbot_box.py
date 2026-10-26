import json
from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.interfaces.box import Box

Ask = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
NOT_AN_OBJECT = 'The arguments must be an object like {"user": "ann"}'
PLATFORMS = ["twitch", "kick", "youtube"]
NEEDS_PASSWORD = ("Streamer.bot only writes in chat for a program that gave its password. In Streamer.bot: "
                  "Servers/Clients → WebSocket Server → tick Authentication and set a password. Type the same "
                  "password into the Password field under Connections → Streamer.bot and press Connect")


class StreamerbotBox(Box):
    """What the streamerbot boxes share (not a box itself: it has no run).

    Streamer.bot's boxes. What happens is built in Streamer.bot as an action; the toolbox runs it by name
    (the picker lists them from the running program) and can hand it arguments, which the action finds as
    %name%."""

    def __init__(self, ask: Ask) -> None:
        self._ask = ask

    async def action_names(self) -> list[str]:
        try:
            answer = await self._ask({"request": "GetActions"})
        except ConnectionError:
            return []
        return sorted(str(a.get("name")) for a in answer.get("actions") or []
                      if isinstance(a, dict) and a.get("name") and a.get("enabled", True))

    @staticmethod
    async def platforms() -> list[str]:
        return list(PLATFORMS)


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
    return {str(key): value for key, value in values.items()}
