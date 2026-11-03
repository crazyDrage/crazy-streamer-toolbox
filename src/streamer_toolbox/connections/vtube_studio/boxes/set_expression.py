from streamer_toolbox.connections.vtube_studio.boxes.vts_expression_box import VtsExpressionBox, Request


class SetExpression(VtsExpressionBox):
    name = "set_expression"
    label = "Set expression"
    help = "Switches an expression (.exp3.json) on or off"
    group = "Expressions"

    def __init__(self, request: Request) -> None:
        super().__init__(request)
        self.options = {"expression": self.expression_files}

    async def run(self, expression: str, active: bool = True) -> None:
        on = bool(active)
        if isinstance(active, str):  # "false" from a variable or typed text
            on = active.strip().casefold() not in ("false", "0", "no", "off", "")
        await self._request("ExpressionActivationRequest", {"expressionFile": expression, "active": on})
