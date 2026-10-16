import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_input import FlowInput
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_step_error import FlowStepError
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.flows.logic_actions import LogicActions
from streamer_toolbox.core.variables.variable_store import VariableStore


class TestFlowRunnerDataWires(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.variables = VariableStore(Path(self.tmp.name) / "variables.json")
        self.calls: list[dict] = []
        self.reads = 0
        self.actions = ActionRegistry()

        async def record(**params):
            self.calls.append(params)

        async def position():
            self.reads += 1
            return {"x": "0.5", "y": -1.0, "model": "Dragon"}

        async def model():
            return "Dragon"

        self.actions.add("a.record", record)
        self.actions.add("a.position", position)
        self.actions.add("a.model", model)
        LogicActions(self.variables).add_to(self.actions)
        self.runner = FlowRunner(self.actions, self.variables)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    async def test_a_box_without_run_wires_runs_when_an_if_needs_its_value(self) -> None:
        # his example: VTS get loaded model → If left
        flow = Flow("f", "F", (FlowNode("n1", "logic.if", {"left": "${box.n2}", "right": "dragon"}),
                               FlowNode("n2", "a.model"),
                               FlowNode("n3", "a.record", {"side": "then"})),
                    (FlowWire("start", "out", "n1"), FlowWire("n1", "then", "n3")))
        await self.runner.run(flow)
        self.assertEqual(self.calls, [{"side": "then"}])

    async def test_a_field_of_a_result_is_wired_on_its_own(self) -> None:
        # his example: VTS get model position → If (Split data is gone: a field is a wire of its own)
        flow = Flow("f", "F", (FlowNode("n1", "a.position"),
                               FlowNode("n3", "logic.if", {"left": "${box.n1.x}", "op": ">", "right": 0}),
                               FlowNode("n4", "a.record", {"x": "${box.n1.x}", "model": "${box.n1.model}"})),
                    (FlowWire("start", "out", "n3"), FlowWire("n3", "then", "n4")))
        await self.runner.run(flow)
        self.assertEqual(self.calls, [{"x": "0.5", "model": "Dragon"}])
        self.assertEqual(self.reads, 2)  # read fresh for each box that needs it, once per box

    async def test_helpers_on_a_wire_give_keys_kinds_and_counts(self) -> None:
        flow = Flow("f", "F", (FlowNode("n1", "a.position"),
                               FlowNode("n2", "a.record", {"keys": "${box.n1.@keys}", "kinds": "${box.n1.@kinds}",
                                                           "count": "${box.n1.@count}",
                                                           "letters": "${box.n1.model.@count}",
                                                           "said": "has ${box.n1.@count} fields"})),
                    (FlowWire("start", "out", "n2"),))
        await self.runner.run(flow)
        self.assertEqual(self.calls, [{"keys": ["x", "y", "model"], "kinds": {"x": "text", "y": "number",
                                                                               "model": "text"},
                                       "count": 3, "letters": 6, "said": "has 3 fields"}])

    async def test_a_typed_value_is_read_for_what_it_holds_and_a_wired_one_keeps_its_kind(self) -> None:
        async def user_id():
            return "12345"

        self.actions.add("a.user_id", user_id)
        flow = Flow("f", "F", (FlowNode("n1", "a.user_id"),
                               FlowNode("typed", "var.set", {"name": "typed", "value": "0.5"}),
                               FlowNode("yes", "var.set", {"name": "yes", "value": "true"}),
                               FlowNode("json", "var.set", {"name": "json", "value": '{"a": [1, 2]}'}),
                               FlowNode("zero", "var.set", {"name": "zero", "value": "007"}),
                               FlowNode("wired", "var.set", {"name": "wired", "value": "${box.n1}"}),
                               FlowNode("mixed", "var.set", {"name": "mixed", "value": "1${box.n1}"}),
                               FlowNode("value", "logic.value", {"value": "42"}),
                               FlowNode("name", "var.set", {"name": "7", "value": "x"})),
                    (FlowWire("start", "out", "typed"), FlowWire("typed", "done", "yes"),
                     FlowWire("yes", "done", "json"), FlowWire("json", "done", "zero"),
                     FlowWire("zero", "done", "wired"), FlowWire("wired", "done", "mixed"),
                     FlowWire("mixed", "done", "value"), FlowWire("value", "done", "name")))
        results = {r["box"]: r["result"] for r in await self.runner.run(flow)}
        self.assertEqual([self.variables.get(n) for n in ("typed", "yes", "json", "zero", "wired", "mixed")],
                         [0.5, True, {"a": [1, 2]}, "007", "12345", "112345"])
        self.assertEqual(results["value"], 42)
        self.assertEqual(self.variables.get("7"), "x")  # only the fields named as typed: a name stays text

    async def test_a_box_that_runs_in_the_flow_gives_its_latest_result(self) -> None:
        flow = Flow("f", "F", (FlowNode("n1", "a.position"), FlowNode("n2", "a.record", {"pos": "${box.n1.y}"})),
                    (FlowWire("start", "out", "n1"), FlowWire("n1", "done", "n2")))
        await self.runner.run(flow)
        self.assertEqual((self.calls, self.reads), ([{"pos": -1.0}], 1))
        self.assertEqual(self.runner.last_result("f", "n1"), (True, {"x": "0.5", "y": -1.0, "model": "Dragon"}))

    async def test_a_box_that_has_not_run_yet_or_an_empty_wire_fails_clearly(self) -> None:
        early = Flow("f", "F", (FlowNode("n1", "a.position"), FlowNode("n2", "a.record", {"pos": "${box.n1}"})),
                     (FlowWire("start", "out", "n2"), FlowWire("n2", "done", "n1")))
        with self.assertRaisesRegex(FlowStepError, "hasn't run yet"):
            await self.runner.run(early)
        empty = Flow("g", "G", (FlowNode("n1", "a.record", {"pos": "${box}"}),), (FlowWire("start", "out", "n1"),))
        with self.assertRaisesRegex(FlowStepError, "no wire leads into it"):
            await self.runner.run(empty)

    async def test_a_data_wire_loop_is_caught(self) -> None:
        flow = Flow("f", "F", (FlowNode("n1", "var.set", {"name": "a", "value": "${box.n2}"}),
                               FlowNode("n2", "var.set", {"name": "b", "value": "${box.n1}"}),
                               FlowNode("n3", "a.record", {"v": "${box.n1}"})),
                    (FlowWire("start", "out", "n3"),))
        with self.assertRaisesRegex(FlowStepError, "loop"):
            await self.runner.run(flow)

    async def test_testing_one_box_uses_what_earlier_boxes_gave_last_time(self) -> None:
        node = FlowNode("n2", "a.record", {"pos": "${box.n1.model}"})
        flow = Flow("f", "F", (FlowNode("n1", "a.position"), node),
                    (FlowWire("start", "out", "n1"), FlowWire("n1", "done", "n2")))
        with self.assertRaisesRegex(RuntimeError, "hasn't run yet"):
            await self.runner.run_node(flow, node)
        await self.runner.run(flow)
        await self.runner.run_node(flow, node)
        self.assertEqual(self.calls[-1], {"pos": "Dragon"})

    async def test_start_gives_what_started_the_flow(self) -> None:
        # a redeem: the viewer's name and text wired straight into a box; a missing field is empty
        node = FlowNode("n1", "a.record", {"who": "${box.start.user}", "said": "${box.start.input}",
                                           "amount": "${box.start.amount}", "none": "${box.start.nope}"})
        flow = Flow("f", "F", (node,), (FlowWire("start", "out", "n1"),),
                    inputs=(FlowInput("amount", 3),))
        await self.runner.run(flow, event={"user": "Kit", "input": "hi"})
        self.assertEqual(self.calls, [{"who": "Kit", "said": "hi", "amount": 3, "none": ""}])
        self.assertEqual(self.runner.last_result("f", "start"), (True, {"user": "Kit", "input": "hi", "amount": 3}))

    async def test_a_flow_with_output_boxes_gives_them_back_as_named_outputs(self) -> None:
        # "Play video"-like inner flow: gives back seconds; the outer flow reads it over a data wire
        inner = Flow("inner", "Inner", (FlowNode("n1", "a.position"),
                                        FlowNode("n2", "logic.output", {"name": "model", "value": "${box.n1.model}"}),
                                        FlowNode("n3", "logic.output", {"name": "done", "value": True})),
                     (FlowWire("start", "out", "n1"), FlowWire("n1", "done", "n2"), FlowWire("n2", "done", "n3")))
        self.assertEqual(inner.outputs, ("model", "done"))
        self.runner.register(inner)
        self.assertEqual(self.actions.get("flow.inner").outputs, {"model": "", "done": ""})
        outer = Flow("outer", "Outer", (FlowNode("n1", "flow.inner"),
                                        FlowNode("n2", "a.record", {"who": "${box.n1.model}"})),
                     (FlowWire("start", "out", "n1"), FlowWire("n1", "done", "n2")))
        await self.runner.run(outer)
        self.assertEqual(self.calls, [{"who": "Dragon"}])
        self.assertEqual(await self.actions.run("flow.inner"), {"model": "Dragon", "done": True})

    def test_a_data_wire_loop_is_found_before_saving(self) -> None:
        loop = Flow("f", "F", (FlowNode("n1", "var.set", {"name": "a", "value": "${box.n2}"}),
                               FlowNode("n2", "var.set", {"name": "b", "value": "x ${box.n3.y} y"}),
                               FlowNode("n3", "var.set", {"name": "c", "value": "${box.n1}"}),
                               FlowNode("n4", "a.record", {"v": "${box.n1}", "w": "${box.start.user}"})))
        self.assertEqual(loop.data_loop(), ["n1", "n2", "n3", "n1"])
        fine = Flow("f", "F", (FlowNode("n1", "a.position"), FlowNode("n2", "a.record", {"v": "${box.n1.x}"}),
                               FlowNode("n3", "a.record", {"v": "${box.n1.y}", "w": "${box.gone}"})))
        self.assertEqual(fine.data_loop(), [])

    async def test_test_run_gives_results_and_the_failure_instead_of_raising(self) -> None:
        flow = Flow("f", "F", (FlowNode("n1", "a.model"), FlowNode("n2", "logic.wait", {"seconds": "soon"})),
                    (FlowWire("start", "out", "n1"), FlowWire("n1", "done", "n2")))
        results, error = await self.runner.test_run(flow)
        self.assertEqual([r["box"] for r in results], ["n1"])
        self.assertEqual((error.node_id, type(error.cause)), ("n2", ValueError))
        self.assertEqual(await self.runner.test_run(Flow("g", "G", (FlowNode("n1", "a.model"),),
                                                         (FlowWire("start", "out", "n1"),))),
                         ([{"box": "n1", "action": "a.model", "result": "Dragon"}], None))

    async def test_test_run_takes_inputs_and_lists_boxes_run_for_a_wire(self) -> None:
        flow = Flow("f", "F", (FlowNode("n1", "a.record", {"x": "${box.n2.x}", "who": "${box.start.who}"}),
                               FlowNode("n2", "logic.value", {"values": {"x": "${box.n3.x}"}}),
                               FlowNode("n3", "a.position")),
                    (FlowWire("start", "out", "n1"),), inputs=(FlowInput("who", None),))
        results, error = await self.runner.test_run(flow, {"who": "Kit"})
        self.assertIsNone(error)
        self.assertEqual(self.calls, [{"x": "0.5", "who": "Kit"}])  # a wired value keeps its kind
        self.assertEqual([(r["box"], r.get("for_wire", False)) for r in results],
                         [("n3", True), ("n2", True), ("n1", False)])

    async def test_test_run_shows_an_error_that_is_not_a_box_failing(self) -> None:
        broken = Flow("f", "F", (FlowNode("n1", "a.model"),), (FlowWire("start", "out", "n1"),))
        self.runner._follow = None  # anything unexpected inside the runner
        results, error = await self.runner.test_run(broken)
        self.assertEqual((results, type(error)), ([], TypeError))
