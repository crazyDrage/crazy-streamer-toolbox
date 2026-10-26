import asyncio
import inspect
import logging
import re
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.numbered_fields import count_field
from streamer_toolbox.core.data.box_value import understand
from streamer_toolbox.core.flows.box_signals import ALONGSIDE, BoxSignals
from streamer_toolbox.core.flows.box_wire import WIRE_IN, field_of
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_gate import FlowGate
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_run import FlowRun
from streamer_toolbox.core.flows.flow_skipped import FlowSkipped
from streamer_toolbox.core.flows.flow_step_error import FlowStepError
from streamer_toolbox.core.flows.flow_stopped import FlowStopped
from streamer_toolbox.core.flows.flow_wire import DONE, INPUT, START
from streamer_toolbox.core.flows.retrigger import ON_RETRIGGER
from streamer_toolbox.core.variables.variable_store import VariableStore

log = logging.getLogger(__name__)
PLACEHOLDER = re.compile(r"\$\{(event|input|var|get|box)\.([\w.@]+)\}")  # @ = a helper (${box.n3.@keys})
# what a start gives back when it only stretched the Wait box of a run that was already going
NO_FOLDER = "No folder"  # the Add box sub group of flows outside a folder
STRETCHED = {"box": START, "action": "flow.stretched", "result": "stretched the wait of the running flow"}
MAX_RUNS = 500  # box runs per flow run (per round of a Repeat / For each / Loop); stops a wire loop
KEEP_RESULTS = 1000  # a Loop running for hours keeps only its latest box results
TEST_PORTS = 20  # Test box on a For each / Loop: the first ports it would fire


class FlowRunner:
    """Runs a flow from its Start box along the wires. All boxes wired to the same output run at the same time;
    a box that fails stops only its own branch, and the flow reports the first failure at the end.

    A box with several outputs picks one by its result (True → first, False → second, or a port name); a result
    that is a list of its port names fires them one after the other (Repeat), an async generator of port names
    likewise, one round at a time (For each sets its variable between rounds). A join action (Wait for all) runs
    once every wire leading into it has arrived; other boxes run each time a wire arrives.

    Data wires: a field set to ${box.n3} (or ${box.n3.x}, one field) takes box n3's result. If n3 has run wires
    into it, that's its latest result in this run; if it has none, it runs right then, every time a box needs it
    (like a Live value), and only gives its result: its own outputs don't fire. ${box.t1.user} is what trigger t1's
    Start box gave (empty when another Start box started the run), ${box.input.seconds} an input; the older
    ${box.start.user} is the event's data and the inputs together (a field it doesn't have is empty).

    Entries: a box with extra run dots (a Loop's "stop") runs once at a time per flow; a wire into one of those
    dots, in any run of the flow, is passed to the running box (BoxSignals) instead of starting anything. With its
    `alongside` field set to ALONGSIDE every run has its own copy: a wire from a run goes to that run's copy, from a
    run without one to every copy.

    Lines: a box with entry_fields (Choose value, End) has a run dot per numbered field; a wire into one starts the
    box with only that field read (a wire into its normal run dot counts as the first).

    Stop: every run (also a Test run) is a task of its own; stop(flow name) cancels the flow's runs, which then
    raise FlowStopped (his round 63: an endless loop needs a way out without restarting the toolbox). A flow it
    started as a box runs on; stop that one by its own name."""

    def __init__(self, actions: ActionRegistry, variables: VariableStore) -> None:
        self._actions = actions
        self._variables = variables
        self._last: dict[tuple[str, str], Any] = {}  # (flow, box) → its latest result in any run or test
        self.gate = FlowGate(self._stretchable)  # a flow started again while it runs: alongside, in line or skipped
        self._running: dict[tuple[str, str], list[tuple[FlowRun, BoxSignals]]] = {}  # (flow, box) → its copies
        self._runs: dict[asyncio.Task, FlowRun] = {}  # the runs going on now (stop)

    async def run(self, flow: Flow, event: dict[str, Any] | None = None,
                  inputs: dict[str, Any] | None = None, start: str = START) -> list[dict[str, Any]]:
        """Runs it to the end from the Start box `start` (a trigger's id; Manual by default); the result of every
        box that ran. Raises FlowSkipped if it's switched off, or set to skip and already running. A start that
        stretched a running wait doesn't run: one "stretched" result."""
        if not flow.enabled:
            raise FlowSkipped(f"flow {flow.label!r} is switched off (Flows page, or its settings in the "
                              "editor)")
        if self.gate.stretch(flow):
            return [dict(STRETCHED)]
        async with self.gate.enter(flow):
            return (await self._run(flow, event, inputs, start=start)).results

    async def test_run(self, flow: Flow, inputs: dict[str, Any] | None = None,
                       event: dict[str, Any] | None = None, start_at: str | None = None,
                       start: str = START) -> tuple[list[dict[str, Any]], Exception | None]:
        """The editor's Test run: runs it and gives back what every box gave (also the ones run for a data wire)
        and the first failure, instead of raising. event: what a trigger would give (its Start box's values),
        start: which Start box it starts at. start_at: a box id: "Test run from here", that box and what is wired
        after it run; a value from a box before it is what that box gave last time (like Test box)."""
        try:
            return (await self._run(flow, event, inputs, start_at=start_at, start=start)).results, None
        except FlowStepError as e:
            return e.results, e
        except Exception as e:  # not a box failing: still show it instead of losing it
            return [], e

    async def _run(self, flow: Flow, event: dict[str, Any] | None, inputs: dict[str, Any] | None,
                   ended: asyncio.Future | None = None, start_at: str | None = None, start: str = START) -> FlowRun:
        defaults = {i.name: i.default for i in flow.inputs if i.default is not None}
        run = FlowRun(flow, event or {}, {**defaults, **(inputs or {})}, test=start_at is not None, ended=ended,
                      start=start)
        task = asyncio.create_task(self._go(run, start_at))
        self._runs[task] = run
        try:
            await task
        except asyncio.CancelledError:
            if not run.stopped:  # cancelled from outside (the toolbox closing): not ours to turn into an error
                raise
            raise FlowStopped(f"flow {flow.label!r} was stopped") from None
        finally:
            self._runs.pop(task, None)
        if run.error is not None:
            if isinstance(run.error, FlowStepError):
                run.error.results = run.results  # what ran before (and beside) the failure, for Test run
            raise run.error
        return run

    def running(self, flow_name: str | None = None) -> int:
        """How many runs of the flow go on now (None: of every flow)."""
        return sum(1 for run in self._runs.values() if flow_name is None or run.flow.name == flow_name)

    def stop(self, flow_name: str | None = None) -> int:
        """Stops the runs of the flow (None: of every flow) where they are; how many were stopped."""
        stopped = 0
        for task, run in list(self._runs.items()):
            if (flow_name is None or run.flow.name == flow_name) and not task.done():
                run.stopped = True
                task.cancel()
                stopped += 1
        return stopped

    async def _go(self, run: FlowRun, start_at: str | None) -> None:
        flow, start = run.flow, run.start
        if start_at is None:
            self._last[(flow.name, start)] = dict(run.event) if start != START else {}  # its Last start, the
            self._last[(flow.name, INPUT)] = dict(run.inputs)                          # kinds of its dots
            await self._follow(run, start, "out")
        else:
            node = flow.node(start_at)
            if node is None:
                raise KeyError(f"box {start_at} isn't in the flow anymore")
            run.arrivals[node.id] = len(flow.wires)  # a "Wait for all" started here doesn't wait for the others
            await self._node(run, node)

    async def run_node(self, flow: Flow, node: FlowNode) -> Any:
        """Runs one box on its own (the editor's Test button); input placeholders get their defaults, data wires
        from boxes that run earlier in the flow use what those gave last time."""
        run = FlowRun(flow, {}, {i.name: i.default for i in flow.inputs if i.default is not None}, test=True)
        result = await self._call(run, node)
        if inspect.isasyncgen(result):  # For each / Loop on its own: just the (first) ports it would fire
            ports = []
            async for item in result:
                ports.append(item[0] if isinstance(item, tuple) else item)
                if len(ports) >= TEST_PORTS:
                    break
            await result.aclose()
            return ports
        self._last[(flow.name, node.id)] = result
        return result

    def last_result(self, flow_name: str, node_id: str) -> tuple[bool, Any]:
        """(True, result) if the box ran (or was tested) since the toolbox started, else (False, None)."""
        key = (flow_name, node_id)
        return key in self._last, self._last.get(key)

    def register(self, flow: Flow) -> None:
        """Makes the flow the action flow.<name>; its inputs become the action's parameters. A flow with Flow
        output boxes gives back {name: value} (orange dots on its box in other flows), others every box's result.

        The End box: its box in another flow goes on when it is reached (the rest of this flow runs on by itself),
        with the End box's values. Without an End box the box goes on when the flow is done."""

        outputs = self.outputs_of(flow)

        async def run_flow(**inputs: Any) -> Any:
            if not flow.enabled:
                raise FlowSkipped(f"flow {flow.label!r} is switched off (Flows page, or its settings in the "
                                  "editor)")
            if self.gate.stretch(flow):
                return {} if outputs else [dict(STRETCHED)]
            ended: asyncio.Future = asyncio.get_running_loop().create_future()

            async def whole() -> FlowRun:
                async with self.gate.enter(flow):
                    return await self._run(flow, None, inputs, ended)

            task = asyncio.create_task(whole())
            await asyncio.wait({task, ended}, return_when=asyncio.FIRST_COMPLETED)
            if ended.done():
                run = ended.result()
                if not task.done():  # the flow runs on by itself; a failure there is only logged
                    task.add_done_callback(_log_failure)
            else:
                run = task.result()  # done without reaching the End box (raises if it failed)
            return dict(run.outputs) if outputs else run.results

        # what the Live page, the SAMMI deck and GET /actions see as its parameters
        run_flow.__signature__ = inspect.Signature([
            inspect.Parameter(i.name, inspect.Parameter.KEYWORD_ONLY,
                              default=inspect.Parameter.empty if i.default is None else i.default)
            for i in flow.inputs])
        self._actions.add(flow.action_name, run_flow, flow.description or f"Runs the flow {flow.label}", flow.label,
                          group=flow.folder or NO_FOLDER, outputs={name: "" for name in outputs},
                          offered=flow.as_box)  # sorted by his folders in Add box (his round 56)

    async def _follow(self, run: FlowRun, source: str, port: str) -> None:
        starts = [(run.flow.node(t), "") for t in run.flow.targets(source, port)]
        for target, entry in run.flow.entries(source, port):
            node = run.flow.node(target)
            if node is not None and entry in self._lines(node):
                starts.append((node, entry))
            elif node is not None and self._starts_it(run, node, entry):
                starts.append((node, ""))  # a Loop's switch while it doesn't loop: it starts
            else:
                self._signal(run, target, entry)
        await asyncio.gather(*(self._node(run, node, line) for node, line in starts if node is not None))

    def outputs_of(self, flow: Flow) -> tuple[str, ...]:
        """What the flow gives back, by name, in box order: the values of the box that ends it (End's lines) and
        the names of the boxes that give back (Flow output; typed names only). The orange dots of its box in other
        flows."""
        names = []
        for node in flow.nodes:
            action = self._actions.get(node.action) if node.action in self._actions else None
            if action and action.ends_flow:
                names += action.lines_named(node.params)
            elif action and action.gives_back:
                names.append(str(node.params.get(action.gives_back, "")).strip())
        return tuple(dict.fromkeys(n for n in names if n and "${" not in n))

    def _stretchable(self, flow: Flow) -> bool:
        """A flow with a switched-on box whose `retrigger` field says what a new start does (Wait: start over /
        add the time): a new start then stretches the running one instead of running."""
        for node in flow.nodes:
            action = self._actions.get(node.action) if node.action in self._actions else None
            mode = node.params.get(action.retrigger) if action and action.retrigger and node.enabled else None
            if mode in ON_RETRIGGER and mode != "nothing":
                return True
        return False

    def _starts_it(self, run: FlowRun, node: FlowNode, entry: str) -> bool:
        """A wire into a toggle dot (Loop's switch) of a box that isn't running starts it; decided here, in one go
        with passing it on, so a box that is about to stop can't be started by the same wire."""
        action = self._actions.get(node.action) if node.action in self._actions else None
        if not action or entry not in action.toggles:
            return False
        copies = self._running.get((run.flow.name, node.id), [])
        return not any(r is run for r, _ in copies) and (not copies or self._alongside(action, node))

    @staticmethod
    def _alongside(action, node: FlowNode) -> bool:
        return bool(action.alongside) and node.params.get(action.alongside) == ALONGSIDE

    def _lines(self, node: FlowNode) -> list[str]:
        """The run dots of a box with lines (Choose value's value_1, value_2, ...); [] for others."""
        return self._actions.get(node.action).entry_lines(node.params) if node.action in self._actions else []

    async def _node(self, run: FlowRun, node: FlowNode, line: str = "") -> None:
        run.count += 1
        if run.count > MAX_RUNS:
            run.fail(FlowStepError(run.flow.name, node.id, node.action,
                                   RuntimeError(f"more than {MAX_RUNS} boxes ran: is there a wire loop?")))
            return
        action = self._actions.get(node.action) if node.action in self._actions else None
        ports = (action.ports_for(node.params) if action else ()) or (DONE,)
        if action and action.join:  # "Wait for all": goes on only when every wire into it has arrived
            run.arrivals[node.id] = run.arrivals.get(node.id, 0) + 1
            if run.arrivals[node.id] < len({w for w in run.flow.wires if w.target == node.id and not w.entry}):
                return
        if not node.enabled:
            run.results.append({"box": node.id, "action": node.action, "skipped": True})
            if len(ports) == 1:  # a switched-off box passes on; a switched-off If stops here
                await self._follow(run, node.id, ports[0])
            return
        if action and action.entries:
            copies = self._running.setdefault((run.flow.name, node.id), [])
            if copies and not self._alongside(action, node):
                run.results.append({"box": node.id, "action": node.action, "result": "already running"})
                return
            copy = (run, BoxSignals())
            copies.append(copy)
            copy[1].use()
            try:
                await self._run_box(run, node, ports, line)
            finally:
                copies.remove(copy)
            return
        await self._run_box(run, node, ports, line)

    async def _run_box(self, run: FlowRun, node: FlowNode, ports: tuple[str, ...], line: str = "") -> None:
        try:
            result = await self._call(run, node, line)
        except Exception as e:
            run.fail(FlowStepError(run.flow.name, node.id, node.action, e))
            return
        if inspect.isasyncgen(result):  # For each: sets its variable, then hands over one port per round
            run.results.append({"box": node.id, "action": node.action, "result": None})
            self._remember(run, node, None)
            try:
                async for port in result:
                    if isinstance(port, tuple):  # (port, value): the box's value for this round (a Loop's round)
                        port, value = port
                        self._remember(run, node, value)
                    before = run.count
                    await self._follow(run, node.id, port)
                    run.count = before  # rounds don't add up: a Loop may go on for hours
                    if len(run.results) > KEEP_RESULTS:
                        del run.results[:-KEEP_RESULTS // 2]
            except Exception as e:
                run.fail(FlowStepError(run.flow.name, node.id, node.action, e))
            return
        run.results.append({"box": node.id, "action": node.action, "result": result})
        self._remember(run, node, result)
        action = self._actions.get(node.action) if node.action in self._actions else None
        if action and action.gives_back:  # a Flow output box: given back under the name in that field
            run.outputs[str(await self._fill(node.params.get(action.gives_back, ""), run, {})).strip()] = result
        if action and action.ends_flow:
            if isinstance(result, dict):
                run.outputs.update(result)  # its values: orange dots of the flow's box in the other flow
            if run.ended is not None and not run.ended.done():
                run.ended.set_result(run)  # its box in the other flow goes on now
        if len(ports) > 1 and isinstance(result, list) and all(p in ports for p in result):
            for port in result:  # e.g. Repeat 3: each, each, each, done; one after the other
                await self._follow(run, node.id, port)
            return
        port = ports[0] if len(ports) == 1 else _port(ports, result)
        await self._follow(run, node.id, port)

    def _signal(self, run: FlowRun, node_id: str, entry: str) -> None:
        """A wire into a box's extra run dot: hands it to that box if it runs (in this or another run)."""
        node = run.flow.node(node_id)
        copies = self._running.get((run.flow.name, node_id), [])
        targets = [s for r, s in copies if r is run] or [s for _, s in copies]  # its own copy, else every one
        for signals in targets:
            signals.send(entry)
        run.results.append({"box": node_id, "action": node.action if node else "",
                            "result": f"{entry}: passed on" if targets else f"{entry}: it wasn't running"})

    async def _call(self, run: FlowRun, node: FlowNode, line: str = "") -> Any:
        """line: the run dot a box with lines was started at; only that field is read (else the first)."""
        pulled: dict[str, Any] = {}  # boxes this box's data wires ran, so two fields from one box run it once
        params = {}
        action = self._actions.get(node.action) if node.action in self._actions else None
        typed, lines = (action.typed, action.value_lines) if action else ((), "")
        typed = (*typed, *action.lines_named(node.params)) if action else typed  # End's values
        entry_lines = self._lines(node)
        if entry_lines:  # only the line that ran it, under the plain name; the others may not have run at all
            arrived = node.params.get(line if line in entry_lines else entry_lines[0], "")
            if arrived == WIRE_IN:
                raise ValueError(f"{line or entry_lines[0]}: no wire leads into it yet (or choose Value for it)")
            fill = self._typed if action.entry_fields in typed else self._fill
            params[action.entry_fields] = await fill(arrived, run, pulled)
        skip = {*entry_lines, count_field(action.entry_fields)} if entry_lines else set()
        for key, value in node.params.items():
            if key in skip:
                continue
            if value == WIRE_IN:
                raise ValueError(f"{key}: no wire leads into it yet (or choose Value for it)")
            if key == lines and isinstance(value, dict):  # a Value box's lines: each one like a typed field
                params[key] = {name: await self._typed(line, run, pulled) for name, line in value.items()}
            elif key in typed:
                params[key] = await self._typed(value, run, pulled)
            else:
                params[key] = await self._fill(value, run, pulled)
        result = await self._actions.run(node.action, **params)
        if node.save_as and not inspect.isasyncgen(result):
            self._variables.set(node.save_as, result)
        return result

    async def _typed(self, value: Any, run: FlowRun, pulled: dict[str, Any]) -> Any:
        """A field that takes any kind: typed by hand it is read for what it holds (0.5 is a number); a wire or a
        ${...} in it keeps the kind it brings."""
        if isinstance(value, str) and not PLACEHOLDER.search(value):
            return understand(value)
        return await self._fill(value, run, pulled)

    async def _fill(self, value: Any, run: FlowRun, pulled: dict[str, Any]) -> Any:
        if not isinstance(value, str):
            return value
        whole = PLACEHOLDER.fullmatch(value)
        if whole:  # keep the value's type ("${var.pos}" → the position object, "${event.amount}" → 5)
            return await self._value(whole.group(1), whole.group(2), run, pulled)
        parts, last = [], 0
        for match in PLACEHOLDER.finditer(value):
            found = await self._value(match.group(1), match.group(2), run, pulled)
            parts += [value[last:match.start()], str(found)]
            last = match.end()
        return "".join(parts) + value[last:]

    async def _value(self, kind: str, path: str, run: FlowRun, pulled: dict[str, Any]) -> Any:
        if kind == "var":
            return self._variables.lookup(path)
        if kind == "get":  # a Live value: "vts.get_model" or "vts.get_model_position.x", read right now
            category, name, *fields = path.split(".")
            return field_of(await self._actions.run(f"{category}.{name}"), ".".join(fields), f"{category}.{name}")
        if kind == "box":  # a data wire: "n3" (its result) or "n3.x" (one field of it)
            node_id, _, fields = path.partition(".")
            started = self._started(run, node_id)
            if started is not None:  # a Start box (what its trigger gave) or the Input box
                first, _, rest = fields.partition(".")
                return field_of(started.get(first, ""), rest, first) if first else started
            if node_id not in pulled:
                pulled[node_id] = await self._box_result(run, node_id)
            return field_of(pulled[node_id], fields, f"box {node_id}")
        source = run.event if kind == "event" else run.inputs
        return source.get(path, "")

    @staticmethod
    def _started(run: FlowRun, node_id: str) -> dict[str, Any] | None:
        """The values of a Start box or the Input box in this run; None for other boxes. A trigger's Start box that
        didn't start this run gives nothing (each Start box on its own, his round 63)."""
        if node_id == INPUT:
            return run.inputs
        if node_id == START:  # files from before round 63 read event and inputs here
            return {**run.event, **run.inputs}
        if run.flow.trigger(node_id) is not None:
            return run.event if node_id == run.start else {}
        return None

    async def _box_result(self, run: FlowRun, node_id: str) -> Any:
        node = run.flow.node(node_id)
        if node is None:
            raise KeyError(f"box {node_id} isn't in the flow anymore")
        action = self._actions.get(node.action) if node.action in self._actions else None
        starts = ["", *(action.starts_at(node.params) if action else ())]  # the run dots that start it
        if any(w.target == node_id and w.entry in starts for w in run.flow.wires):  # it runs in the flow: what it gave
            if node_id in run.values:
                return run.values[node_id]
            known, last = self.last_result(run.flow.name, node_id)
            if run.test and known:
                return last
            raise RuntimeError(f"box {node_id} hasn't run yet: wire it to run before this box, or take away the "
                               "wires into it so it runs whenever its value is needed")
        if not node.enabled:
            raise RuntimeError(f"box {node_id} is switched off, so it gives no value")
        if node_id in run.pulling:
            raise RuntimeError(f"box {node_id} needs its own value (the data wires go round in a loop)")
        run.count += 1
        if run.count > MAX_RUNS:
            raise RuntimeError(f"more than {MAX_RUNS} boxes ran: is there a wire loop?")
        run.pulling.add(node_id)
        try:
            result = await self._call(run, node)
        finally:
            run.pulling.discard(node_id)
        if inspect.isasyncgen(result):  # For each gives no value
            await result.aclose()
            result = None
        run.results.append({"box": node.id, "action": node.action, "result": result, "for_wire": True})
        self._remember(run, node, result)
        return result

    def _remember(self, run: FlowRun, node: FlowNode, result: Any) -> None:
        run.values[node.id] = result
        self._last[(run.flow.name, node.id)] = result


def _log_failure(task: asyncio.Task) -> None:
    if not task.cancelled() and task.exception():
        log.warning("a flow ran on after its End box and failed: %s", task.exception())


def _port(ports: tuple[str, ...], result: Any) -> str:
    if isinstance(result, str) and result in ports:
        return result
    return ports[0] if result else ports[1]
