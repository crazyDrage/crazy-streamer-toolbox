import tempfile
import unittest
from pathlib import Path
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.text_actions import TextActions
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_pack import FlowPack
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.logic_actions import LogicActions
from streamer_toolbox.core.learn.learn_library import LearnLibrary
from streamer_toolbox.core.variables.variable_store import VariableStore


class TestLearnExamplesRun(unittest.IsolatedAsyncioTestCase):
    """The Learn tab's examples run from their trigger to the end (chat and sound are stand-ins here)."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.chat: list[str] = []
        self.sounds: list[str] = []
        actions = ActionRegistry()
        variables = VariableStore(Path(self._dir.name) / "variables")
        LogicActions(variables).add_to(actions)
        TextActions().add_to(actions)
        actions.add("twitch.send_chat", self._say, "")
        actions.add("sound.play", self._play, "")
        self.runner = FlowRunner(actions, variables)

    def tearDown(self) -> None:
        self._dir.cleanup()

    async def _say(self, message: str) -> None:
        self.chat.append(message)

    async def _play(self, file: str, volume: float = 1.0) -> None:
        self.sounds.append(file)

    @staticmethod
    def _flow(topic_id: str) -> Flow:
        return FlowPack.from_text(LearnLibrary().get(topic_id).flows.read_text(encoding="utf-8")).flows[0]

    async def _run(self, topic_id: str, event: dict[str, Any]) -> None:
        flow = self._flow(topic_id)
        await self.runner.run(flow, event, start=flow.triggers[0].id)

    async def test_chat_counter(self) -> None:
        await self._run("chat_counter", {"user": "Kit", "command": "!lizard"})
        await self._run("chat_counter", {"user": "Kit", "command": "!lizard"})
        self.assertEqual(self.chat, ["Lizards so far: 1", "Lizards so far: 2"])

    async def test_build_a_message(self) -> None:
        await self._run("build_a_message", {"user": "Kit", "bits": 100})
        self.assertEqual(self.chat, ["Kit just gave 100 Bits!"])

    async def test_sound_on_redeem(self) -> None:
        await self._run("sound_on_redeem", {"user": "Kit", "reward": "Play a sound"})
        self.assertEqual(self.sounds, [""])  # the file is his to pick


if __name__ == "__main__":
    unittest.main()
