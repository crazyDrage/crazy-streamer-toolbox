from streamer_toolbox.core.actions.fixed_choices import fixed_choices
from streamer_toolbox.core.data.box_value import to_number
from streamer_toolbox.core.flows.boxes.calculate import MATH, work_out
from streamer_toolbox.core.variables.boxes.variable_box import VariableBox
from streamer_toolbox.core.variables.variable_store import VariableStore


class MathOnVariable(VariableBox):
    name = "add"
    label = "Math on variable"
    help = "Works a number variable out with + - * / and keeps the result in it, e.g. count + 1 or score * 2; gives " \
           "the new value. A variable that doesn't exist yet starts at 0"
    group = "Variables"
    labels = {"op": "Sign", "amount": "Number"}
    variable_fields = ("name",)

    def __init__(self, variables: VariableStore) -> None:
        super().__init__(variables)
        self.options = {"name": self.names, "op": fixed_choices(MATH)}

    async def run(self, name: str, op: str = "+", amount: float = 1) -> float:
        current = to_number(self.variables.get(name, 0))
        if current is None:
            raise ValueError(f"variable {name} is not a number ({self.variables.get(name)!r})")
        total = work_out(current, op, amount)
        self.variables.set(name, total)
        return total
