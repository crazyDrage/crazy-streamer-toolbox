import asyncio
import inspect
import re
import tempfile
import unittest
from dataclasses import MISSING, fields, replace
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.registered_action import RegisteredAction
from streamer_toolbox.core.data.list_actions import ListActions
from streamer_toolbox.core.flows.debug_actions import DebugActions
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.flows.logic_actions import LogicActions
from streamer_toolbox.core.interfaces.box import OPTIONS, Box
from streamer_toolbox.core.variables.variable_store import VariableStore
from tests.fakes.fake_plugin_context import FakePluginContext

REPO = Path(__file__).resolve().parents[2]
# code that runs or draws flows, where a box must never be special because of its name
FLOW_CODE = [*(REPO / "src/streamer_toolbox/core/flows").glob("*.py"),
             *(REPO / "src/streamer_toolbox/gui/components/flow_editor").glob("*.py")]
BY_NAME = re.compile(r"""\.action\s*(==|!=|\bin\b)\s*["'A-Z(]""")


class TestPluginParity(unittest.IsolatedAsyncioTestCase):
    """His round 56: "every input/output and box logic we make can be created with a plugin, too". A new box
    option that plugins can't pass, or a box that is special by its name, fails here."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.variables = VariableStore(Path(self.tmp.name) / "variables")
        self.actions = ActionRegistry()
        self.calls: list[dict] = []

        async def record(**params):
            self.calls.append(params)

        self.actions.add("a.record", record)
        self.runner = FlowRunner(self.actions, self.variables)
        self.ctx = FakePluginContext("p", self.actions)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_every_box_option_is_a_keyword_plugins_can_pass_and_is_documented(self) -> None:
        keywords = inspect.signature(ActionRegistry.add).parameters
        documented = (REPO / "docs/ai/code/action.md").read_text(encoding="utf-8")
        for option in OPTIONS:
            with self.subTest(option=option):
                self.assertIn(option, keywords)
                self.assertIn(f"`{option}", documented)

    def test_every_box_option_is_an_attribute_of_the_box_class_with_the_same_default(self) -> None:
        for option in fields(RegisteredAction):
            if option.name not in OPTIONS:
                continue
            default = option.default if option.default is not MISSING else option.default_factory()
            with self.subTest(option=option.name):
                self.assertEqual(getattr(Box, option.name), default)

    def test_a_box_class_can_make_every_box_the_flow_logic_has(self) -> None:
        own = ActionRegistry()
        LogicActions(self.variables).add_to(own)
        ListActions(self.variables).add_to(own)
        DebugActions().add_to(own)
        plugin = FakePluginContext("p", ActionRegistry())
        for action in own.all(include_flow_only=True):
            with self.subTest(box=action.name):
                rebuilt = type("Rebuilt", (Box,), {"name": action.name, "label": action.label,
                                                   "help": action.description, "run": staticmethod(action.handler),
                                                   **{option: getattr(action, option) for option in OPTIONS}})
                plugin.add(rebuilt())
                self.assertEqual(replace(plugin.actions.get(f"p.{action.name}"), name=action.name), action)

    def test_a_plugin_can_make_every_box_the_flow_logic_has(self) -> None:
        own = ActionRegistry()
        LogicActions(self.variables).add_to(own)
        ListActions(self.variables).add_to(own)
        DebugActions().add_to(own)
        plugin = FakePluginContext("p", ActionRegistry())
        for action in own.all(include_flow_only=True):
            with self.subTest(box=action.name):
                plugin.add_action(action.name, action.handler, action.description, action.label,
                                  **{option: getattr(action, option) for option in OPTIONS})
                self.assertEqual(replace(plugin.actions.get(f"p.{action.name}"), name=action.name), action)

    def test_no_flow_code_treats_a_box_by_its_name(self) -> None:
        for path in FLOW_CODE:
            if path.name.startswith("old_"):  # reading flow files from before: their old box names
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                with self.subTest(file=path.name, line=number):
                    self.assertIsNone(BY_NAME.search(line), line.strip())

    async def test_a_plugins_own_loop_end_and_wait_work_like_the_toolboxs(self) -> None:
        ctx = self.ctx

        async def pulse(pause: float = 0.01):
            signals = ctx.box_signals()

            async def rounds():
                count = 0
                while not signals.has("stop", "flip"):
                    count += 1
                    yield "each", {"count": count}
                    await signals.wait_for(pause, "stop", "flip")
                yield "stopped"
            return rounds()

        async def finish(**values):
            return values

        async def hold(seconds: float = 0.0, again: str = "nothing") -> int:
            retrigger = ctx.retrigger()
            return await retrigger.wait(seconds, again) if retrigger else 0

        ctx.add_action("pulse", pulse, ports=("each", "stopped"), entries=("stop", "flip"), toggles=("flip",),
                       outputs={"count": "number"}, flow_only=True)
        ctx.add_action("finish", finish, named_lines=True, ends_flow=True, once_per_flow=True, flow_only=True)
        ctx.add_action("hold", hold, retrigger="again", flow_only=True)
        nodes = (FlowNode("loop", "p.pulse"), FlowNode("tick", "a.record", {"n": "${box.loop.count}"}),
                 FlowNode("done", "p.finish", {"state": "looping"}))
        inner = Flow("blink", "Blink", nodes, (FlowWire("start", "out", "loop", "flip"),
                                                FlowWire("loop", "each", "tick"), FlowWire("start", "out", "done")))
        self.assertEqual(self.runner.outputs_of(inner), ("state",))
        held = Flow("held", "Held", (FlowNode("wait", "p.hold", {"again": "add"}),))
        self.assertTrue(self.runner._stretchable(held))  # a new start stretches its hold box, like a Wait's
        self.assertFalse(self.runner._stretchable(inner))
        self.runner.register(inner)
        self.assertEqual(await self.actions.run("flow.blink"), {"state": "looping"})  # went on at the end box
        while len(self.calls) < 3:
            await asyncio.sleep(0.01)
        self.assertEqual(self.calls[:3], [{"n": 1}, {"n": 2}, {"n": 3}])
        await self.actions.run("flow.blink")  # the flip dot again: it stops
        await asyncio.sleep(0.05)
        count = len(self.calls)
        await asyncio.sleep(0.05)
        self.assertEqual(len(self.calls), count)


if __name__ == "__main__":
    unittest.main()
