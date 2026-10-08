from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry

Request = Callable[..., Awaitable[dict[str, Any]]]  # (message type, data) → VTS's answer data


class VtsExpressionActions:
    """VTube Studio boxes for the model's expressions (.exp3.json): switch one on or off, ask whether one is on."""

    def __init__(self, request: Request) -> None:
        self._request = request

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("vts.set_expression", self.set_expression, "Switches an expression (.exp3.json) on or off",
                    "Set expression", group="Expressions", options={"expression": self.expression_files})
        actions.add("vts.expression_active", self.expression_active, "Whether an expression is on now "
                    "(true / false)", "Is expression on", group="Expressions",
                    options={"expression": self.expression_files})

    async def set_expression(self, expression: str, active: bool = True) -> None:
        on = bool(active)
        if isinstance(active, str):  # "false" from a variable or typed text
            on = active.strip().casefold() not in ("false", "0", "no", "off", "")
        await self._request("ExpressionActivationRequest", {"expressionFile": expression, "active": on})

    async def expression_active(self, expression: str) -> bool:
        states = await self._request("ExpressionStateRequest", {"details": False, "expressionFile": expression})
        return any(e.get("active") for e in states.get("expressions", []))

    async def expression_files(self) -> list[str]:
        states = await self._request("ExpressionStateRequest", {"details": False})
        return [e["file"] for e in states.get("expressions", [])]
