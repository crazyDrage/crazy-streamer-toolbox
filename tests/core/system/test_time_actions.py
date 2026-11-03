import unittest
from datetime import datetime

from streamer_toolbox.core.system.boxes.date_and_time import DateAndTime
from streamer_toolbox.core.system.boxes.seconds_since import SecondsSince

MOMENT = datetime(2026, 10, 1, 21, 5, 9).timestamp()


class TestTimeActions(unittest.IsolatedAsyncioTestCase):
    async def test_now(self) -> None:
        now = await DateAndTime(lambda: MOMENT).run("%H:%M")
        self.assertEqual((now["hour"], now["minute"], now["weekday"], now["date"], now["text"]),
                         (21, 5, "thursday", "2026-10-01", "21:05"))
        self.assertEqual((await DateAndTime(lambda: MOMENT).run())["text"], "2026-10-01 21:05")

    async def test_since(self) -> None:
        self.assertEqual(await SecondsSince(lambda: MOMENT + 90).run(MOMENT), 90)
        with self.assertRaises(ValueError):
            await SecondsSince().run("yesterday")


if __name__ == "__main__":
    unittest.main()
