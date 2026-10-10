import unittest
from datetime import datetime

from streamer_toolbox.core.system.time_actions import TimeActions

MOMENT = datetime(2026, 10, 1, 21, 5, 9).timestamp()


class TestTimeActions(unittest.IsolatedAsyncioTestCase):
    async def test_now(self) -> None:
        now = await TimeActions(lambda: MOMENT).now("%H:%M")
        self.assertEqual((now["hour"], now["minute"], now["weekday"], now["date"], now["text"]),
                         (21, 5, "thursday", "2026-10-01", "21:05"))
        self.assertEqual((await TimeActions(lambda: MOMENT).now())["text"], "2026-10-01 21:05")

    async def test_since(self) -> None:
        self.assertEqual(await TimeActions(lambda: MOMENT + 90).since(MOMENT), 90)
        with self.assertRaises(ValueError):
            await TimeActions().since("yesterday")


if __name__ == "__main__":
    unittest.main()
