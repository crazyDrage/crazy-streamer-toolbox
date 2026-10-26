from streamer_toolbox.connections.vtube_studio.boxes.vts_expression_box import VtsExpressionBox, Request


class IsExpressionOn(VtsExpressionBox):
    name = "expression_active"
    label = "Is expression on"
    help = "Whether an expression is on now (true / false)"
    group = "Expressions"

    def __init__(self, request: Request) -> None:
        super().__init__(request)
        self.options = {"expression": self.expression_files}

    async def run(self, expression: str) -> bool:
        states = await self._request("ExpressionStateRequest", {"details": False, "expressionFile": expression})
        return any(e.get("active") for e in states.get("expressions", []))
