from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.flows.boxes.calculate import Calculate
from streamer_toolbox.core.flows.boxes.choose_value import ChooseValue
from streamer_toolbox.core.flows.boxes.clamp import Clamp
from streamer_toolbox.core.flows.boxes.color_from_numbers import ColorFromNumbers
from streamer_toolbox.core.flows.boxes.end import End
from streamer_toolbox.core.flows.boxes.flow_output import FlowOutput
from streamer_toolbox.core.flows.boxes.for_each import ForEach
from streamer_toolbox.core.flows.boxes.if_box import IfBox
from streamer_toolbox.core.flows.boxes.loop import Loop
from streamer_toolbox.core.flows.boxes.random_number import RandomNumber
from streamer_toolbox.core.flows.boxes.repeat import Repeat
from streamer_toolbox.core.flows.boxes.round_number import RoundNumber
from streamer_toolbox.core.flows.boxes.switch import Switch
from streamer_toolbox.core.flows.boxes.value import Value
from streamer_toolbox.core.flows.boxes.wait import Wait
from streamer_toolbox.core.flows.boxes.wait_for_all import WaitForAll
from streamer_toolbox.core.variables.boxes.get_variable import GetVariable
from streamer_toolbox.core.variables.boxes.math_on_variable import MathOnVariable
from streamer_toolbox.core.variables.boxes.set_field import SetField
from streamer_toolbox.core.variables.boxes.set_variable import SetVariable
from streamer_toolbox.core.variables.variable_store import VariableStore


class LogicActions:
    """The boxes that aren't a service, one Box class each (core/flows/boxes/, core/variables/boxes/): If,
    Switch, Choose value, Repeat, For each, Loop, Wait, Wait for all, Random number, Calculate, Round, Clamp,
    Colour from numbers, Value, End, Flow output; and Set / Get variable, Math on variable, Set field."""

    def __init__(self, variables: VariableStore) -> None:
        self._variables = variables

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (IfBox(), Repeat(), ForEach(self._variables), Loop(), Wait(), WaitForAll(), RandomNumber(),
                    Calculate(), RoundNumber(), Clamp(), ColorFromNumbers(), Switch(), Value(), ChooseValue(), End(),
                    FlowOutput()):
            actions.add_box(box, "logic")
        for box in (SetVariable(self._variables), MathOnVariable(self._variables), GetVariable(self._variables),
                    SetField(self._variables)):
            actions.add_box(box, "var")
