from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.interfaces.box import Box

Request = Callable[..., Awaitable[dict[str, Any]]]


class VtsExpressionBox(Box):
    """What the vts expression boxes share (not a box itself: it has no run).

    VTube Studio boxes for the model's expressions (.exp3.json): switch one on or off, ask whether one is on."""

    def __init__(self, request: Request) -> None:
        self._request = request

    async def expression_files(self) -> list[str]:
        states = await self._request("ExpressionStateRequest", {"details": False})
        return [e["file"] for e in states.get("expressions", [])]
