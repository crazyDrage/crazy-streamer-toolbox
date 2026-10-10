import unittest

from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.gui.components.flow_editor.start_examples import StartExamples


class TestStartExamples(unittest.TestCase):
    def test_trigger_values_then_examples(self) -> None:
        triggers = [FlowTrigger("custom", {"trigger": "lizard"}),
                    FlowTrigger("twitch.redeem", {"reward": "Lizard", "reward_id": "r1"})]
        values = StartExamples.values(triggers, None)
        self.assertEqual(values["trigger"], "lizard")
        self.assertEqual((values["reward"], values["reward_id"]), ("Lizard", "r1"))
        self.assertEqual((values["user"], values["input"]), ("TestViewer", "hello"))
        self.assertIn("platform", values)

    def test_the_last_real_start_wins(self) -> None:
        values = StartExamples.values([FlowTrigger("twitch.chat", {"command": "!lizard*"})],
                                      {"user": "VexFan", "command": "!lizard", "message": "!lizard go"})
        self.assertEqual((values["user"], values["command"], values["message"]), ("VexFan", "!lizard", "!lizard go"))
        self.assertEqual(StartExamples.values([], None), {})
