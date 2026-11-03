import asyncio
from typing import Any

from streamer_toolbox.core.actions.fixed_choices import fixed_choices
from streamer_toolbox.core.flows.boxes.if_box import OPERATORS, IfBox
from streamer_toolbox.core.variables.boxes.variable_box import VariableBox
from streamer_toolbox.core.variables.variable_store import VariableStore


class WaitUntilVariable(VariableBox):
    """SAMMI's Wait Until Variable: it doesn't look again and again, it looks each time a variable changes."""

    name = "wait_until"
    label = "Wait until variable"
    help = "Waits until a variable passes the check (the same checks as If), then goes on. Gives true, or false " \
           "when the time ran out first (wire it into an If for that case). A variable that doesn't exist counts " \
           "as empty text, and waits on under < >"
    group = "Wait"
    flow_only = True
    labels = {"op": "Check", "value": "Compare with"}
    variable_fields = ("name",)
    hints = {"seconds": "The longest it waits, e.g. 10. 0 = no limit"}

    def __init__(self, variables: VariableStore) -> None:
        super().__init__(variables)
        self.options = {"name": self.names, "op": fixed_choices(OPERATORS)}

    async def run(self, name: str, op: str = "==", value: Any = "", seconds: float = 10.0) -> bool:
        changed = asyncio.Event()
        self.variables.on_change(changed.set)
        try:
            loop = asyncio.get_running_loop()
            end = loop.time() + float(seconds)
            while not await self._passes(name, op, value):
                changed.clear()
                left = end - loop.time()
                if float(seconds) > 0 and left <= 0:
                    return False
                try:
                    await asyncio.wait_for(changed.wait(), left if float(seconds) > 0 else None)
                except TimeoutError:
                    return await self._passes(name, op, value)
            return True
        finally:
            self.variables.off_change(changed.set)

    async def _passes(self, name: str, op: str, value: Any) -> bool:
        try:
            return await IfBox().run(self.variables.get(name, ""), op, value)
        except ValueError:
            if name in self.variables.names():  # a text variable under < >: a mistake in the flow, say so
                raise
            return False  # not there yet, so no number to compare: keep waiting
