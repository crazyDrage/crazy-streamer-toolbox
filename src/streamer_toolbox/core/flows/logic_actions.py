import asyncio
import copy
import random
from collections.abc import AsyncIterator
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.numbered_fields import numbered_fields
from streamer_toolbox.core.data.box_value import same, to_list, understand
from streamer_toolbox.core.flows.box_signals import BoxSignals
from streamer_toolbox.core.flows.retrigger import ON_RETRIGGER, current_retrigger
from streamer_toolbox.core.variables.variable_store import VariableStore

OPERATORS = ["==", "!=", "contains", "<", ">", "<=", ">="]
MATH = ["+", "-", "*", "/"]
CASE = "case"  # Switch: case_1, case_2, ... (as many as it has), one output each, then "else"
SHORTEST_PAUSE = 0.05  # between Loop rounds: a round of quick boxes can't take the toolbox over


class LogicActions:
    """The boxes that aren't a service: If (then / else), Repeat, For each, Loop (start / stop), Wait,
    Random number, Calculate, Set / Add to variable, Set field."""

    def __init__(self, variables: VariableStore) -> None:
        self._variables = variables

    def add_to(self, actions: ActionRegistry) -> None:
        async def operators() -> list[str]:
            return OPERATORS

        async def names() -> list[str]:
            return self._variables.names()

        async def math_operators() -> list[str]:
            return MATH

        actions.add("logic.if", self.compare, "Goes on through 'then' if the check is true, else through 'else'. "
                    "Text is compared without caring about upper/lower case", "If", group="If",
                    options={"op": operators}, ports=("then", "else"), flow_only=True,
                    labels={"left": "Value", "op": "Check", "right": "Compare with"},
                    hints={"op": "contains = the text is somewhere in it; < > need two numbers"})
        actions.add("logic.repeat", self.repeat, "Runs what's wired to 'each' this many times, one after the "
                    "other, then goes on through 'done'", "Repeat", group="Repeat", ports=("each", "done"),
                    flow_only=True, labels={"times": "How many times"})
        actions.add("logic.for_each", self.for_each, "Runs what's wired to 'each' once for every value in the list, "
                    "one after the other, with the value in the variable 'item'; then goes on through 'done'",
                    "For each", group="Repeat", options={"item": names}, ports=("each", "done"), flow_only=True,
                    labels={"items": "List", "item": "Each value goes in variable"})

        actions.add("logic.loop", self.loop, "Runs what's wired to 'each' again and again, one round after the "
                    "other, until a wire reaches its 'stop' dot (e.g. the same button pressed again, through a "
                    "flow input start / stop). Then 'stopped' goes on. A second start while it loops does nothing",
                    "Loop (start / stop)", group="Repeat", ports=("each", "stopped"), flow_only=True,
                    entries=("stop",), labels={"pause": "Pause between rounds (s)"},
                    hints={"rounds": "0 = until stopped; else stop after this many rounds",
                           "pause": "Waits this long after each round. A stop ends the loop after the round "
                                    "that's running. The flow must Run alongside (top of the page), so the "
                                    "stop can get in"})

        async def retrigger_modes() -> dict[str, str]:
            return ON_RETRIGGER

        actions.add("logic.wait", self.wait, "Waits, then goes on. If started again: a new start of the flow "
                    "during the wait (or before it) doesn't run the flow again, it starts the wait over or adds "
                    "the time again, e.g. light on, Wait 2 s, light off: every redeem keeps the light on longer. "
                    "Gives how many times it was stretched", "Wait", group="Wait",
                    options={"if_started_again": retrigger_modes}, flow_only=True,
                    hints={"seconds": "How long, e.g. 2 or 0.5",
                           "if_started_again": "The flow is started again while it waits: start the 2 s over, or "
                                               "add 2 s more. That start doesn't run the flow a second time"})
        actions.add("logic.wait_for_all", self.wait_for_all, "Goes on once every box wired into it is done, e.g. "
                    "after boxes that run at the same time. Not after an If: only one of its sides ever arrives",
                    "Wait for all", group="Wait", flow_only=True, join=True)
        actions.add("logic.random", self.random_number, "A whole random number from lowest to highest (both "
                    "included), e.g. 1 to 100 for a d100. Save it in a variable", "Random number", group="Random",
                    flow_only=True, labels={"lowest": "From", "highest": "To"})
        actions.add("logic.math", self.calculate, "a + - * / b, e.g. the model's x minus 0.2 to move it left. "
                    "Wire a number into a (or b), and this box's result into the next box",
                    "Calculate", group="Math", options={"op": math_operators}, flow_only=True,
                    labels={"a": "First number", "op": "Sign", "b": "Second number"})
        actions.add("logic.round", self.round_number, "Rounds a number to that many decimals (0 = a whole "
                    "number)", "Round", group="Math", flow_only=True,
                    hints={"decimals": "0 = a whole number, 2 = like 1.25"})
        actions.add("logic.clamp", self.clamp, "Keeps a number between lowest and highest, e.g. a power a viewer "
                    "typed into 1 to 10", "Clamp", group="Math", flow_only=True,
                    labels={"lowest": "At least", "highest": "At most"})
        actions.add("logic.switch", self.switch, "Goes on through the first case that equals the value (a case "
                    "may list several, e.g. 'ra, right_arm'), else through 'else'. Like If, for more than two ways: "
                    "+ Add case for as many as you need", "Switch", group="If", ports=("else",), port_fields=CASE,
                    flow_only=True, hints={"value": "What to look at, e.g. what the viewer typed",
                                           CASE: "Several words with a comma, e.g. ra, right_arm"})
        actions.add("logic.value", self.value, "A value you type once (e.g. your model's name) and wire into as "
                    "many boxes as you like: change it here, every box gets it. Numbers, true/false and JSON stay "
                    "what they are", "Value", group="Flow", flow_only=True,
                    hints={"value": "Wire its orange result dot into the fields that need it; it needs no run wire"},
                    typed=("value",))
        actions.add("logic.end", self.end, "The end of this flow when another flow uses it as a box: there that "
                    "box goes on as soon as an End box is reached. Give End boxes names (found, not found, ...) and "
                    "the box gets one output per name", "End", group="Flow", flow_only=True,
                    hints={"name": "Empty = the box's one output. A name = its own output on the box"})
        actions.add("logic.output", self.output, "What this flow gives back when another flow uses it as a box: "
                    "each Flow output box becomes an orange dot on that box, named like this box",
                    "Flow output", group="Flow", flow_only=True, typed=("value",))
        actions.add("var.set", self.set_variable, "Stores a value in a variable (kept in a file)", "Set variable",
                    group="Variables", options={"name": names}, typed=("value",))
        actions.add("var.add", self.add_to_variable, "Adds to a number variable (a minus number takes away); "
                    "a variable that doesn't exist yet starts at 0", "Add to variable", group="Variables",
                    options={"name": names})
        actions.add("var.set_field", self.set_field, "Sets one field of an object variable (a.b for a field "
                    "inside a field); a variable that doesn't exist yet starts as an empty object", "Set field",
                    group="Variables", options={"name": names}, typed=("value",))

    @staticmethod
    async def compare(left: Any, op: str = "==", right: Any = "") -> bool:
        if op not in OPERATORS:
            raise ValueError(f"unknown check {op!r}; use one of {', '.join(OPERATORS)}")
        if op == "contains":
            return str(right).casefold() in str(left).casefold()
        a, b = _number(left), _number(right)
        if a is None or b is None:  # text: only equal / not equal make sense
            a, b = str(left).casefold(), str(right).casefold()
        checks = {"==": a == b, "!=": a != b}
        if op in checks:
            return checks[op]
        if isinstance(a, str):
            raise ValueError(f"{op} needs two numbers, got {left!r} and {right!r}")
        return {"<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b}[op]

    @staticmethod
    async def repeat(times: int = 2) -> list[str]:
        return ["each"] * max(int(times), 0) + ["done"]

    @staticmethod
    async def loop(rounds: int = 0, pause: float = 0.0) -> AsyncIterator[str]:
        """Hands the runner one round at a time until its stop dot gets a wire (or the rounds are done)."""
        rounds, pause = int(rounds or 0), max(float(pause or 0), SHORTEST_PAUSE)
        signals = BoxSignals.current()  # None on its own (Test box): then it only counts rounds

        async def go() -> AsyncIterator[str]:
            done = 0
            while not (signals and signals.has("stop")):
                yield "each"
                done += 1
                if 0 < rounds <= done:
                    break
                if signals:
                    await signals.wait_for("stop", pause)
                else:
                    await asyncio.sleep(pause)
            yield "stopped"

        return go()

    @staticmethod
    async def end(name: str = "") -> str:
        return str(name).strip()

    @staticmethod
    async def value(value: Any = "") -> Any:
        return value  # typed by hand it arrives read already (typed); a wire keeps its kind

    async def for_each(self, items: Any, item: str = "item") -> AsyncIterator[str]:
        """Checks the list first (a bad list fails the box), then hands the runner one round at a time."""
        values = to_list(items)
        self._variables.set(item, None)  # also checks the variable name before the first round

        async def rounds() -> AsyncIterator[str]:
            for value in values:
                self._variables.set(item, value)
                yield "each"
            yield "done"

        return rounds()

    @staticmethod
    async def random_number(lowest: int = 1, highest: int = 100) -> int:
        return random.randint(int(lowest), int(highest))

    @staticmethod
    async def calculate(a: float, op: str = "+", b: float = 0) -> float:
        x, y = _number(a), _number(b)
        if x is None or y is None:
            raise ValueError(f"Calculate needs two numbers, got {a!r} and {b!r}")
        if op not in MATH:
            raise ValueError(f"unknown sign {op!r}; use one of {' '.join(MATH)}")
        if op == "/" and y == 0:
            raise ValueError("can't divide by 0")
        result = {"+": x + y, "-": x - y, "*": x * y, "/": x / y if y else 0.0}[op]
        return int(result) if result == int(result) else round(result, 10)

    @staticmethod
    async def round_number(number: float, decimals: int = 0) -> float:
        value = _number(number)
        if value is None:
            raise ValueError(f"{number!r} is not a number")
        rounded = round(value, int(decimals))
        return int(rounded) if int(decimals) <= 0 else rounded

    @staticmethod
    async def clamp(number: float, lowest: float = 0, highest: float = 100) -> float:
        value, low, high = _number(number), _number(lowest), _number(highest)
        if value is None or low is None or high is None:
            raise ValueError(f"Clamp needs numbers, got {number!r}, {lowest!r}, {highest!r}")
        result = min(max(value, low), high)
        return int(result) if result == int(result) else result

    @staticmethod
    async def switch(value: Any, **cases: Any) -> str:
        """cases: case_1, case_2, ... (and "cases", how many there are)."""
        for port in numbered_fields(CASE, cases):
            case = str(cases.get(port, ""))
            if case.strip() and any(same(value, c.strip()) for c in case.split(",")):
                return port
        return "else"

    @staticmethod
    async def wait(seconds: float = 1.0, if_started_again: str = "nothing") -> int:
        """How many times a new start stretched it (0 for a plain wait)."""
        retrigger = current_retrigger.get()
        if if_started_again not in ON_RETRIGGER:
            raise ValueError(f"unknown 'If started again' {if_started_again!r}; use one of {', '.join(ON_RETRIGGER)}")
        if if_started_again == "nothing" or retrigger is None or not retrigger.open:  # Test run: a plain wait
            await asyncio.sleep(float(seconds))
            return 0
        return await retrigger.wait(float(seconds), if_started_again)

    @staticmethod
    async def output(name: str, value: Any = "") -> Any:
        """The FlowRunner collects it under `name`."""
        return value

    @staticmethod
    async def wait_for_all() -> None:
        """Does nothing itself; the FlowRunner holds it back until all its wires arrived."""

    async def set_variable(self, name: str, value: Any = "") -> Any:
        self._variables.set(name, value)
        return value

    async def add_to_variable(self, name: str, amount: float = 1) -> float:
        current = _number(self._variables.get(name, 0))
        if current is None:
            raise ValueError(f"variable {name} is not a number ({self._variables.get(name)!r})")
        total = current + float(amount)
        total = int(total) if total == int(total) else total
        self._variables.set(name, total)
        return total

    async def set_field(self, name: str, field: str, value: Any = "") -> dict[str, Any]:
        whole = understand(self._variables.get(name, {}))  # also an object typed into Set variable as JSON text
        if not isinstance(whole, dict):
            raise ValueError(f"variable {name} is not an object ({whole!r})")
        whole = copy.deepcopy(whole)
        *path, last = str(field).split(".")
        inner = whole
        for part in path:
            if not isinstance(inner.get(part, {}), dict):
                raise ValueError(f"{name}.{part} is not an object")
            inner = inner.setdefault(part, {})
        inner[last] = value
        self._variables.set(name, whole)
        return whole


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
