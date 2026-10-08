import asyncio
import inspect
import logging
import re
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.box_value import understand
from streamer_toolbox.core.flows.box_signals import BoxSignals
from streamer_toolbox.core.flows.box_wire import WIRE_IN, field_of
from streamer_toolbox.core.flows.flow import END_ACTION, END_KEY, OUTPUT_ACTION, Flow
from streamer_toolbox.core.flows.flow_gate import FlowGate
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_run import FlowRun
from streamer_toolbox.core.flows.flow_step_error import FlowStepError
from streamer_toolbox.core.flows.flow_wire import DONE, START
from streamer_toolbox.core.variables.variable_store import VariableStore

log = logging.getLogger(__name__)
PLACEHOLDER = re.compile(r"\$\{(event|input|var|get|box)\.([\w.@]+)\}")  # @ = a helper (${box.n3.@keys})
# what a start gives back when it only stretched the Wait box of a run that was already going
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
    (like a Live value), and only gives its result: its own outputs don't fire. ${box.start.user} is what started
    the flow: the event's data and the flow's inputs (a field it doesn't have is empty, like ${event.x}).

    Entries: a box with extra run dots (a Loop's "stop") runs once at a time per flow; a wire into one of those
    dots, in any run of the flow, is passed to the running box (BoxSignals) instead of starting anything."""

    def __init__(self, actions: ActionRegistry, variables: VariableStore) -> None:
        self._actions = actions
        self._variables = variables
        self._last: dict[tuple[str, str], Any] = {}  # (flow, box) → its latest result in any run or test
        self.gate = FlowGate()  # a flow started again while it runs: alongside, in line or skipped (when_busy)
        self._running: dict[tuple[str, str], BoxSignals] = {}  # (flow, box) → a box with entries that runs

    async def run(self, flow: Flow, event: dict[str, Any] | None = None,
                  inputs: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Runs it to the end; the result of every box that ran. Raises FlowSkipped if it's set to skip and
        already running. A start that stretched a running wait doesn't run: one "stretched" result."""
        if self.gate.stretch(flow):
            return [dict(STRETCHED)]
        async with self.gate.enter(flow):
            return (await self._run(flow, event, inputs)).results

    async def test_run(self, flow: Flow, inputs: dict[str, Any] | None = None,
                       event: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], Exception | None]:
        """The editor's Test run: runs it and gives back what every box gave (also the ones run for a data wire)
        and the first failure, instead of raising. event: what a trigger would give (Start box values)."""
        try:
            return (await self._run(flow, event, inputs)).results, None
        except FlowStepError as e:
            return e.results, e
        except Exception as e:  # not a box failing: still show it instead of losing it
            return [], e

    async def _run(self, flow: Flow, event: dict[str, Any] | None, inputs: dict[str, Any] | None,
                   ended: asyncio.Future | None = None) -> FlowRun:
        defaults = {i.name: i.default for i in flow.inputs if i.default is not None}
        run = FlowRun(flow, event or {}, {**defaults, **(inputs or {})}, ended=ended)
        self._last[(flow.name, START)] = {**run.event, **run.inputs}  # lets Split find the fields of a trigger
        await self._follow(run, START, "out")
        if run.error is not None:
            if isinstance(run.error, FlowStepError):
                run.error.results = run.results  # what ran before (and beside) the failure, for Test run
            raise run.error
        return run

    async def run_node(self, flow: Flow, node: FlowNode) -> Any:
        """Runs one box on its own (the editor's Test button); input placeholders get their defaults, data wires
        from boxes that run earlier in the flow use what those gave last time."""
        run = FlowRun(flow, {}, {i.name: i.default for i in flow.inputs if i.default is not None}, test=True)
        result = await self._call(run, node)
        if inspect.isasyncgen(result):  # For each / Loop on its own: just the (first) ports it would fire
            ports = []
            async for port in result:
                ports.append(port)
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

        End boxes: its box in another flow goes on when one is reached (the rest of this flow runs on by itself);
        named End boxes are the box's outputs (one per name, like an If's then / else). Without an End box the box
        goes on when the flow is done."""
        ends = flow.ends

        async def run_flow(**inputs: Any) -> Any:
            if self.gate.stretch(flow):
                return {} if flow.outputs or ends else [dict(STRETCHED)]
            ended: asyncio.Future = asyncio.get_running_loop().create_future()

            async def whole() -> FlowRun:
                async with self.gate.enter(flow):
                    return await self._run(flow, None, inputs, ended)

            task = asyncio.create_task(whole())
            await asyncio.wait({task, ended}, return_when=asyncio.FIRST_COMPLETED)
            if ended.done():
                end, run = ended.result()
                if not task.done():  # the flow runs on by itself; a failure there is only logged
                    task.add_done_callback(_log_failure)
            else:
                end, run = None, task.result()  # done without an End box (raises if it failed)
            if not (flow.outputs or ends):
                return run.results
            result = dict(run.outputs)
            if ends:
                result[END_KEY] = end or ""  # "" = it ended without reaching a named End box: no output fires
            return result

        # what the Live page, the SAMMI deck and GET /actions see as its parameters
        run_flow.__signature__ = inspect.Signature([
            inspect.Parameter(i.name, inspect.Parameter.KEYWORD_ONLY,
                              default=inspect.Parameter.empty if i.default is None else i.default)
            for i in flow.inputs])
        self._actions.add(flow.action_name, run_flow, flow.description or f"Runs the flow {flow.label}", flow.label,
                          group="Run a flow", outputs={name: "" for name in flow.outputs}, ports=ends)

    async def _follow(self, run: FlowRun, source: str, port: str) -> None:
        targets = [run.flow.node(t) for t in run.flow.targets(source, port)]
        for target, entry in run.flow.entries(source, port):
            self._signal(run, target, entry)
        await asyncio.gather(*(self._node(run, node) for node in targets if node is not None))

    async def _node(self, run: FlowRun, node: FlowNode) -> None:
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
            key = (run.flow.name, node.id)
            if key in self._running:
                run.results.append({"box": node.id, "action": node.action, "result": "already running"})
                return
            self._running[key] = signals = BoxSignals()
            signals.use()
            try:
                await self._run_box(run, node, ports)
            finally:
                self._running.pop(key, None)
            return
        await self._run_box(run, node, ports)

    async def _run_box(self, run: FlowRun, node: FlowNode, ports: tuple[str, ...]) -> None:
        try:
            result = await self._call(run, node)
        except Exception as e:
            run.fail(FlowStepError(run.flow.name, node.id, node.action, e))
            return
        if inspect.isasyncgen(result):  # For each: sets its variable, then hands over one port per round
            run.results.append({"box": node.id, "action": node.action, "result": None})
            self._remember(run, node, None)
            try:
                async for port in result:
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
        if node.action == OUTPUT_ACTION:
            run.outputs[str(await self._fill(node.params.get("name", ""), run, {})).strip()] = result
        if node.action == END_ACTION and run.ended is not None and not run.ended.done():
            run.ended.set_result((str(result or "").strip(), run))  # its box in the other flow goes on now
        if isinstance(result, dict) and END_KEY in result:  # a flow box with named End boxes
            if result[END_KEY] in ports:
                await self._follow(run, node.id, result[END_KEY])
            return
        if len(ports) > 1 and isinstance(result, list) and all(p in ports for p in result):
            for port in result:  # e.g. Repeat 3: each, each, each, done; one after the other
                await self._follow(run, node.id, port)
            return
        port = ports[0] if len(ports) == 1 else _port(ports, result)
        await self._follow(run, node.id, port)

    def _signal(self, run: FlowRun, node_id: str, entry: str) -> None:
        """A wire into a box's extra run dot: hands it to that box if it runs (in this or another run)."""
        node = run.flow.node(node_id)
        signals = self._running.get((run.flow.name, node_id))
        if signals is not None:
            signals.send(entry)
        run.results.append({"box": node_id, "action": node.action if node else "",
                            "result": f"{entry}: passed on" if signals else f"{entry}: it wasn't running"})

    async def _call(self, run: FlowRun, node: FlowNode) -> Any:
        pulled: dict[str, Any] = {}  # boxes this box's data wires ran, so two fields from one box run it once
        params = {}
        typed = self._actions.get(node.action).typed if node.action in self._actions else ()
        for key, value in node.params.items():
            if value == WIRE_IN:
                raise ValueError(f"{key}: no wire leads into it yet (or choose Value for it)")
            params[key] = await self._fill(value, run, pulled)
            if key in typed and isinstance(value, str) and not PLACEHOLDER.search(value):
                params[key] = understand(value)  # typed by hand: 0.5 is a number; a wire keeps its kind
        result = await self._actions.run(node.action, **params)
        if node.save_as and not inspect.isasyncgen(result):
            self._variables.set(node.save_as, result)
        return result

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
            if node_id == START:  # what started it: trigger data and flow inputs
                started = {**run.event, **run.inputs}
                first, _, rest = fields.partition(".")
                return field_of(started.get(first, ""), rest, first) if first else started
            if node_id not in pulled:
                pulled[node_id] = await self._box_result(run, node_id)
            return field_of(pulled[node_id], fields, f"box {node_id}")
        source = run.event if kind == "event" else run.inputs
        return source.get(path, "")

    async def _box_result(self, run: FlowRun, node_id: str) -> Any:
        node = run.flow.node(node_id)
        if node is None:
            raise KeyError(f"box {node_id} isn't in the flow anymore")
        if any(w.target == node_id and not w.entry for w in run.flow.wires):  # it runs in the flow: what it gave
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
