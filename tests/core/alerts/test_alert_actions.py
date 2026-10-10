import asyncio
import unittest

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.alerts.alert_actions import AlertActions
from streamer_toolbox.core.alerts.alert_queue import AlertQueue


class TestAlertActions(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.queue = AlertQueue(gap=0, sleep=self._sleep)
        self.inbox = self.queue.listen()
        self.actions = ActionRegistry()
        AlertActions(self.queue).add_to(self.actions)

    @staticmethod
    async def _sleep(seconds: float) -> None:
        await asyncio.sleep(0)

    async def test_show_alert_from_a_flow(self) -> None:
        result = await self.actions.run("alert.show", text="Dragon just followed!", highlight="Dragon",
                                        seconds="3", volume="0.5", wait="true")
        self.assertEqual(result, {"overlays": 1, "in_front": 0})
        alert = self.inbox.get_nowait()["alert"]
        self.assertEqual((alert["text"], alert["highlights"], alert["seconds"], alert["volume"]),
                         ("Dragon just followed!", ["Dragon"], 3.0, 0.5))
        self.assertEqual(self.actions.get("alert.show").category_title, "Alerts")

    async def test_an_empty_alert_is_refused_and_clear_counts(self) -> None:
        with self.assertRaisesRegex(ValueError, "needs a text, a picture or a sound"):
            await self.actions.run("alert.show", text=" ")
        await self.actions.run("alert.show", text="one")
        await self.actions.run("alert.show", text="two")
        self.assertEqual(await self.actions.run("alert.clear"), 2)


if __name__ == "__main__":
    unittest.main()
