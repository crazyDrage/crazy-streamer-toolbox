import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.flow_trigger_router import FlowTriggerRouter
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.variables.variable_store import VariableStore


class TestFlowTriggerRouterStartBoxes(unittest.IsolatedAsyncioTestCase):
    """His round 63: an event starts the flow at the Start box of the trigger that fits it."""

    async def test_the_run_starts_at_the_matching_triggers_start_box(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            actions, calls = ActionRegistry(), []

            async def record(**params):
                calls.append(params)

            actions.add("a.record", record)
            runner = FlowRunner(actions, VariableStore(folder / "v.json"))
            library = FlowLibrary(FlowStore(folder / "flows"), FlowStore(folder / "t"), runner, actions)
            nodes = (FlowNode("redeem", "a.record", {"redeem": "${box.t1.user}"}),
                     FlowNode("chat", "a.record", {"chat": "${box.t2.user}", "redeemer": "${box.t1.user}"}),
                     FlowNode("button", "a.record", {"button": 1}))
            library.save(Flow("f", "F", nodes, (FlowWire("t1", "out", "redeem"), FlowWire("t2", "out", "chat"),
                                                FlowWire("start", "out", "button")),
                              (FlowTrigger("twitch.redeem", {"reward": "Lizard"}, "t1"),
                               FlowTrigger("twitch.chat", {"command": "!lizard"}, "t2"),
                               FlowTrigger("twitch.chat", {"message": "*"}, "t3"))))
            router = FlowTriggerRouter(library, runner)
            await router.handle("twitch.chat", {"command": "!lizard", "message": "!lizard", "user": "Kit"})
            await router.handle("twitch.redeem", {"reward": "Lizard", "user": "Vex"})
        # the chat fits t2 and t3: the first one starts it, once; a Start box that didn't start the run is empty
        self.assertEqual(calls, [{"chat": "Kit", "redeemer": ""}, {"redeem": "Vex"}])


if __name__ == "__main__":
    unittest.main()
