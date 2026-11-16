import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.cache.remembered_actions import RememberedActions
from streamer_toolbox.core.cache.remembered_values import RememberedValues
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.variables.variable_store import VariableStore


class TestRememberedValue(unittest.IsolatedAsyncioTestCase):
    """The box in a flow (his round 90): run → found / no value; no value → ask → its 'set' dot → found. The next
    box reads its value on both ways."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.actions = ActionRegistry()
        RememberedActions(RememberedValues(Path(self.tmp.name) / "remembered.json")).add_to(self.actions)
        self.asked: list[str] = []
        self.sent: list[object] = []

        async def ask(user: str) -> str:
            self.asked.append(user)
            return f"/pictures/{user}.png"

        async def send(picture: object) -> None:
            self.sent.append(picture)

        self.actions.add("a.ask", ask)
        self.actions.add("a.send", send)
        self.runner = FlowRunner(self.actions, VariableStore(Path(self.tmp.name) / "variables.json"))
        nodes = (FlowNode("rv", "cache.value", {"key": "${box.t1.user_id}", "value": "${box.ask}",
                                                "group": "pfp", "max_age": "10", "most": "100"}),
                 FlowNode("ask", "a.ask", {"user": "${box.t1.user_id}"}),
                 FlowNode("send", "a.send", {"picture": "${box.rv.value}"}))
        wires = (FlowWire("t1", "out", "rv"), FlowWire("rv", "found", "send"), FlowWire("rv", "no_value", "ask"),
                 FlowWire("ask", "done", "rv", "set"))
        self.flow = Flow("chat", "Chat", nodes, wires, (FlowTrigger("chat", {}, "t1"),))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    async def _chat(self, user_id: str) -> None:
        await self.runner.run(self.flow, {"user_id": user_id}, start="t1")

    async def test_asks_once_per_person_then_finds_it(self) -> None:
        for user in ("11", "11", "22", "11"):
            await self._chat(user)
        self.assertEqual(["11", "22"], self.asked)
        self.assertEqual(["/pictures/11.png", "/pictures/11.png", "/pictures/22.png", "/pictures/11.png"], self.sent)

    async def test_its_set_dot_is_drawn_and_starts_it(self) -> None:
        action = self.actions.get("cache.value")
        self.assertEqual(["set"], action.starts_at({}))
        self.assertEqual({"value"}, action.start_only(""))  # 'run' doesn't read (or pull) the value
        self.assertEqual(set(), action.start_only("set"))

    async def test_an_empty_name_is_refused(self) -> None:
        with self.assertRaisesRegex(Exception, "Name is empty"):
            await self._chat("")


if __name__ == "__main__":
    unittest.main()
