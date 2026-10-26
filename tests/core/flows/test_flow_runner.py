import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from streamer_toolbox.core.actions.action_description import describe_action
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_input import FlowInput
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_step_error import FlowStepError
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.flows.logic_actions import LogicActions
from streamer_toolbox.core.variables.variable_store import VariableStore


def chain(*nodes: FlowNode) -> tuple[FlowWire, ...]:
    wires, previous, port = [], "start", "out"
    for node in nodes:
        wires.append(FlowWire(previous, port, node.id))
        previous, port = node.id, "done"
    return tuple(wires)


class TestFlowRunner(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.variables = VariableStore(Path(self.tmp.name) / "variables.json")
        self.calls: list[dict] = []
        self.actions = ActionRegistry()

        async def record(**params):
            self.calls.append(params)
            return "ok"

        async def boom():
            raise ValueError("no")

        async def slow(label: str):
            await asyncio.sleep(0.05)
            self.calls.append({"slow": label})

        async def position():
            return {"x": 0.5, "y": -1.0, "rotation": 0, "size": 20}

        self.actions.add("a.record", record)
        self.actions.add("a.boom", boom)
        self.actions.add("a.slow", slow)
        self.actions.add("a.position", position)
        LogicActions(self.variables).add_to(self.actions)
        self.runner = FlowRunner(self.actions, self.variables)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    async def test_runs_a_chain_skips_switched_off_boxes_and_fills_event_values(self) -> None:
        nodes = (FlowNode("n1", "a.record", {"n": 1, "who": "hi ${event.user}"}),
                 FlowNode("n2", "a.record", {"n": 2}, enabled=False),
                 FlowNode("n3", "a.record", {"n": 3, "amount": "${event.amount}"}))
        results = await self.runner.run(Flow("f", "F", nodes, chain(*nodes)), {"user": "vex", "amount": 5})
        self.assertEqual(self.calls, [{"n": 1, "who": "hi vex"}, {"n": 3, "amount": 5}])
        self.assertTrue(results[1]["skipped"])

    async def test_a_failing_box_stops_its_branch_only(self) -> None:
        nodes = (FlowNode("n1", "a.boom"), FlowNode("n2", "a.record", {"n": 2}), FlowNode("n3", "a.record", {"n": 3}))
        wires = (FlowWire("start", "out", "n1"), FlowWire("n1", "done", "n2"), FlowWire("start", "out", "n3"))
        with self.assertRaisesRegex(FlowStepError, r"stopped at box n1 \(a.boom\): no"):
            await self.runner.run(Flow("f", "F", nodes, wires))
        self.assertEqual(self.calls, [{"n": 3}])

    async def test_boxes_on_one_output_run_at_the_same_time(self) -> None:
        nodes = (FlowNode("a", "a.slow", {"label": "a"}), FlowNode("b", "a.slow", {"label": "b"}),
                 FlowNode("c", "a.record", {"n": "after b"}))
        wires = (FlowWire("start", "out", "a"), FlowWire("start", "out", "b"), FlowWire("b", "done", "c"))
        started = asyncio.get_running_loop().time()
        await self.runner.run(Flow("f", "F", nodes, wires))
        self.assertLess(asyncio.get_running_loop().time() - started, 0.09)  # not 0.1: both slept together
        self.assertEqual(self.calls[-1], {"n": "after b"})
        self.assertEqual(len(self.calls), 3)

    async def test_saved_result_feeds_a_later_box_and_if_picks_a_branch(self) -> None:
        self.variables.set("model", "CrazyDrage Human (Ready to Rig)")
        nodes = (FlowNode("pos", "a.position", save_as="spot"),
                 FlowNode("check", "logic.if", {"left": "${var.model}", "op": "contains", "right": "human"}),
                 FlowNode("yes", "a.record", {"position": "${var.spot}", "x": "x=${var.spot.x}"}),
                 FlowNode("no", "a.record", {"branch": "else"}))
        wires = (FlowWire("start", "out", "pos"), FlowWire("pos", "done", "check"),
                 FlowWire("check", "then", "yes"), FlowWire("check", "else", "no"))
        await self.runner.run(Flow("f", "F", nodes, wires))
        spot = {"x": 0.5, "y": -1.0, "rotation": 0, "size": 20}
        self.assertEqual(self.variables.get("spot"), spot)
        self.assertEqual(self.calls, [{"position": spot, "x": "x=0.5"}])

    async def test_repeat_runs_its_branch_in_turn_then_goes_on(self) -> None:
        self.variables.set("spin", 360)
        nodes = (FlowNode("loop", "logic.repeat", {"times": 4}),
                 FlowNode("turn", "var.add", {"name": "spin", "amount": -90}),
                 FlowNode("show", "a.record", {"at": "${var.spin}"}),
                 FlowNode("end", "a.record", {"end": "${var.spin}"}))
        wires = (FlowWire("start", "out", "loop"), FlowWire("loop", "each", "turn"), FlowWire("turn", "done", "show"),
                 FlowWire("loop", "done", "end"))
        await self.runner.run(Flow("f", "F", nodes, wires))
        self.assertEqual(self.calls, [{"at": 270}, {"at": 180}, {"at": 90}, {"at": 0}, {"end": 0}])

    async def test_for_each_runs_its_branch_per_value_then_goes_on(self) -> None:
        self.variables.set("vts_saves", ["desk", "couch"])
        nodes = (FlowNode("loop", "logic.for_each", {"items": "${var.vts_saves}", "item": "save"}, save_as="x"),
                 FlowNode("slow", "a.slow", {"label": "${var.save}"}),
                 FlowNode("end", "a.record", {"end": "${var.save}"}))
        wires = (FlowWire("start", "out", "loop"), FlowWire("loop", "each", "slow"), FlowWire("loop", "done", "end"))
        await self.runner.run(Flow("f", "F", nodes, wires))
        self.assertEqual(self.calls, [{"slow": "desk"}, {"slow": "couch"}, {"end": "couch"}])
        self.assertIsNone(self.variables.get("x"))
        self.assertEqual(await self.runner.run_node(Flow("f", "F", nodes, wires), nodes[0]), ["each", "each", "done"])

    def _loop_flow(self, rounds: int = 0) -> Flow:
        """Start → If input do == stop → the Loop's stop dot, else → its start; each round → record."""
        nodes = (FlowNode("ask", "logic.if", {"left": "${input.do}", "op": "==", "right": "stop"}),
                 FlowNode("loop", "logic.loop", {"rounds": rounds}),
                 FlowNode("round", "a.record", {"round": 1}),
                 FlowNode("end", "a.record", {"end": 1}))
        wires = (FlowWire("start", "out", "ask"), FlowWire("ask", "then", "loop", "stop"),
                 FlowWire("ask", "else", "loop"), FlowWire("loop", "each", "round"),
                 FlowWire("loop", "stopped", "end"))
        return Flow("f", "F", nodes, wires, inputs=(FlowInput("do", "start"),))

    async def test_loop_runs_until_another_run_reaches_its_stop_dot(self) -> None:
        flow = self._loop_flow()
        looping = asyncio.create_task(self.runner.run(flow, inputs={"do": "start"}))
        while len(self.calls) < 3:
            await asyncio.sleep(0.01)
        again = await self.runner.run(flow, inputs={"do": "start"})
        self.assertIn({"box": "loop", "action": "logic.loop", "result": "already running"}, again)
        stopped = await self.runner.run(flow, inputs={"do": "stop"})
        self.assertIn({"box": "loop", "action": "logic.loop", "result": "stop: passed on"}, stopped)
        await asyncio.wait_for(looping, 1)
        self.assertEqual(self.calls[-1], {"end": 1})
        self.assertTrue(all(c == {"round": 1} for c in self.calls[:-1]))
        late = await self.runner.run(flow, inputs={"do": "stop"})
        self.assertIn({"box": "loop", "action": "logic.loop", "result": "stop: it wasn't running"}, late)

    async def test_the_switch_dot_starts_the_loop_and_stops_it_the_next_time(self) -> None:
        nodes = (FlowNode("loop", "logic.loop"), FlowNode("round", "a.record", {"round": 1}),
                 FlowNode("end", "a.record", {"end": 1}), FlowNode("count", "a.record", {"n": "${box.loop.round}"}))
        flow = Flow("f", "F", nodes, (FlowWire("start", "out", "loop", "switch"), FlowWire("loop", "each", "round"),
                                      FlowWire("loop", "stopped", "end"), FlowWire("round", "done", "count")))
        looping = asyncio.create_task(self.runner.run(flow))
        await asyncio.wait_for(self._calls_reach(6), 1)
        self.assertEqual(self.calls[:6], [{"round": 1}, {"n": 1}, {"round": 1}, {"n": 2}, {"round": 1}, {"n": 3}])
        stopped = await self.runner.run(flow)
        self.assertIn({"box": "loop", "action": "logic.loop", "result": "switch: passed on"}, stopped)
        await asyncio.wait_for(looping, 1)
        self.assertEqual(self.calls[-1], {"end": 1})
        before = len(self.calls)
        again = asyncio.create_task(self.runner.run(flow))  # and the next one starts it again
        await asyncio.wait_for(self._calls_reach(before + 1), 1)
        self.assertEqual(self.calls[before], {"round": 1})
        await self.runner.run(flow)
        await asyncio.wait_for(again, 1)

    async def _calls_reach(self, count: int) -> None:
        while len(self.calls) < count:
            await asyncio.sleep(0.01)

    async def test_loop_with_rounds_ends_by_itself_and_rounds_dont_add_up(self) -> None:
        with mock.patch("streamer_toolbox.core.flows.flow_runner.MAX_RUNS", 6):
            await asyncio.wait_for(self.runner.run(self._loop_flow(rounds=8)), 3)
        self.assertEqual(self.calls, [{"round": 1}] * 8 + [{"end": 1}])

    async def test_test_box_on_a_loop_gives_its_first_ports(self) -> None:
        flow = self._loop_flow()
        ports = await self.runner.run_node(flow, flow.node("loop"))
        self.assertEqual(ports, ["each"] * 20)

    async def test_a_value_box_feeds_several_boxes_without_a_run_wire(self) -> None:
        nodes = (FlowNode("v", "logic.value", {"value": "CrazyDrage Human"}),
                 FlowNode("w", "logic.value", {"value": "5"}),
                 FlowNode("r1", "a.record", {"model": "${box.v}", "n": "${box.w}"}),
                 FlowNode("r2", "a.record", {"again": "${box.v}"}))
        await self.runner.run(Flow("f", "F", nodes, chain(nodes[2], nodes[3])))
        self.assertEqual(self.calls, [{"model": "CrazyDrage Human", "n": 5}, {"again": "CrazyDrage Human"}])

    async def test_each_line_of_a_value_box_is_wired_by_its_name_and_read_for_what_it_holds(self) -> None:
        self.variables.set("who", "Kit")
        nodes = (FlowNode("v", "logic.value", {"values": {"power": "10", "zip": "007", "hi": "hi ${var.who}"}}),
                 FlowNode("r", "a.record", {"p": "${box.v.power}", "z": "${box.v.zip}", "h": "${box.v.hi}"}))
        await self.runner.run(Flow("f", "F", nodes, chain(nodes[1])))
        self.assertEqual(self.calls, [{"p": 10, "z": "007", "h": "hi Kit"}])

    async def test_get_variable_reads_the_variable_each_time_a_box_needs_it(self) -> None:
        self.variables.set("count", 1)
        nodes = (FlowNode("g", "var.get", {"name": "count"}),
                 FlowNode("r1", "a.record", {"n": "${box.g}"}),
                 FlowNode("m", "var.add", {"name": "count", "op": "*", "amount": "5"}),
                 FlowNode("r2", "a.record", {"n": "${box.g}"}))
        await self.runner.run(Flow("f", "F", nodes, chain(*nodes[1:])))
        self.assertEqual(self.calls, [{"n": 1}, {"n": 5}])

    async def test_an_end_box_lets_the_flow_box_go_on_while_the_flow_runs_on(self) -> None:
        inner = Flow("inner", "Inner", (FlowNode("e", "logic.end"), FlowNode("late", "a.slow", {"label": "after end"})),
                     (FlowWire("start", "out", "e"), FlowWire("e", "done", "late")))
        self.runner.register(inner)
        outer_nodes = (FlowNode("y", "flow.inner"), FlowNode("next", "a.record", {"next": 1}))
        await self.runner.run(Flow("outer", "Outer", outer_nodes, chain(*outer_nodes)))
        self.assertEqual(self.calls, [{"next": 1}])  # the next box ran before the inner flow's slow box
        await asyncio.sleep(0.1)
        self.assertEqual(self.calls, [{"next": 1}, {"slow": "after end"}])  # which still ran

    async def test_the_flow_box_has_one_output_also_with_an_end_box(self) -> None:
        inner = Flow("size", "Size", (FlowNode("e", "logic.end"),), (FlowWire("start", "out", "e"),))
        self.runner.register(inner)
        self.assertEqual(self.actions.get("flow.size").ports, ())
        outer_nodes = (FlowNode("s", "flow.size"), FlowNode("b", "a.record", {"was": "after"}))
        await self.runner.run(Flow("outer", "Outer", outer_nodes, chain(*outer_nodes)))
        self.assertEqual(self.calls, [{"was": "after"}])

    async def test_without_an_end_box_the_flow_box_waits_for_the_whole_flow(self) -> None:
        inner = Flow("inner", "Inner", (FlowNode("s", "a.slow", {"label": "inside"}),), (FlowWire("start", "out", "s"),))
        self.runner.register(inner)
        outer_nodes = (FlowNode("y", "flow.inner"), FlowNode("next", "a.record", {"next": 1}))
        await self.runner.run(Flow("outer", "Outer", outer_nodes, chain(*outer_nodes)))
        self.assertEqual(self.calls, [{"slow": "inside"}, {"next": 1}])

    async def test_a_test_run_can_bring_what_a_trigger_would_give(self) -> None:
        nodes = (FlowNode("n1", "a.record", {"who": "${event.user}", "start": "${box.start.reward}"}),)
        flow = Flow("f", "F", nodes, chain(*nodes))
        results, error = await self.runner.test_run(flow, {}, {"user": "TestViewer", "reward": "Lizard"})
        self.assertIsNone(error)
        self.assertEqual(self.calls, [{"who": "TestViewer", "start": "Lizard"}])
        self.assertEqual(self.runner.last_result("f", "start"), (True, {}))  # Manual Start gives nothing

    async def test_a_test_run_from_a_box_runs_it_and_what_comes_after(self) -> None:
        nodes = (FlowNode("n1", "a.record", {"n": 1}), FlowNode("n2", "a.record", {"n": 2}),
                 FlowNode("n3", "a.record", {"n": 3}))
        results, error = await self.runner.test_run(Flow("f", "F", nodes, chain(*nodes)), start_at="n2")
        self.assertIsNone(error)
        self.assertEqual(self.calls, [{"n": 2}, {"n": 3}])
        self.assertEqual([r["box"] for r in results], ["n2", "n3"])

    async def test_live_values_are_read_when_the_box_runs(self) -> None:
        models = iter(["Dragon", "Human"])

        async def model() -> str:
            return next(models)

        self.actions.add("a.model", model, live=True)
        nodes = (FlowNode("check", "logic.if", {"left": "${get.a.model}", "op": "==", "right": "dragon"}),
                 FlowNode("yes", "a.record", {"pos": "${get.a.position}", "text": "x=${get.a.position.x}"}))
        wires = (FlowWire("start", "out", "check"), FlowWire("check", "then", "yes"))
        flow = Flow("f", "F", nodes, wires)
        await self.runner.run(flow)
        await self.runner.run(flow)  # now the model is Human: else, which has no wire
        self.assertEqual(self.calls, [{"pos": {"x": 0.5, "y": -1.0, "rotation": 0, "size": 20}, "text": "x=0.5"}])
        self.assertEqual([a.name for a in self.actions.live()], ["a.model"])
        bad = (FlowNode("n", "a.record", {"x": "${get.a.position.z}"}),)
        with self.assertRaisesRegex(FlowStepError, "no field 'z'"):
            await self.runner.run(Flow("f", "F", bad, chain(*bad)))

    async def test_wait_for_all_goes_on_once_after_the_parallel_boxes(self) -> None:
        nodes = (FlowNode("a", "a.slow", {"label": "a"}), FlowNode("b", "a.record", {"n": "b"}),
                 FlowNode("all", "logic.wait_for_all"), FlowNode("next", "a.record", {"n": "after all"}))
        wires = (FlowWire("start", "out", "a"), FlowWire("start", "out", "b"), FlowWire("a", "done", "all"),
                 FlowWire("b", "done", "all"), FlowWire("all", "done", "next"))
        await self.runner.run(Flow("f", "F", nodes, wires))
        self.assertEqual(self.calls, [{"n": "b"}, {"slow": "a"}, {"n": "after all"}])

    async def test_a_wire_loop_is_stopped(self) -> None:
        nodes = (FlowNode("a", "a.record", {"n": 1}),)
        wires = (FlowWire("start", "out", "a"), FlowWire("a", "done", "a"))
        with self.assertRaisesRegex(FlowStepError, "wire loop"):
            await self.runner.run(Flow("f", "F", nodes, wires))

    async def test_register_makes_it_an_action_with_its_inputs_as_params(self) -> None:
        nodes = (FlowNode("n1", "a.record", {"file": "${input.video}", "vol": "${input.volume}"}),)
        self.runner.register(Flow("sound", "Sound", nodes, chain(*nodes),
                                  inputs=(FlowInput("video"), FlowInput("volume", "80"))))
        params = describe_action(self.actions.get("flow.sound"))["params"]
        self.assertEqual(params, [{"name": "video", "required": True}, {"name": "volume", "required": False}])
        await self.actions.run("flow.sound", video="clip.mp4")
        self.assertEqual(self.calls, [{"file": "clip.mp4", "vol": "80"}])
        self.assertEqual(self.actions.get("flow.sound").label, "Sound")


if __name__ == "__main__":
    unittest.main()
