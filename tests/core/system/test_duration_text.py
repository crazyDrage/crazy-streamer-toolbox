import unittest

from streamer_toolbox.core.system.boxes.duration_text import DurationText


class TestDurationText(unittest.IsolatedAsyncioTestCase):
    async def test_the_biggest_unit_and_the_one_below(self) -> None:
        box = DurationText()
        for seconds, text in ((0, "0 s"), (45, "45 s"), (60, "1 min"), (125, "2 min 5 s"), (3600, "1 h"),
                              (4980, "1 h 23 min"), (5020.9, "1 h 23 min"), (86400 + 300, "1 d"),
                              (2 * 86400 + 3 * 3600, "2 d 3 h"), ("90", "1 min 30 s"), (-5, "0 s")):
            with self.subTest(seconds):
                self.assertEqual(await box.run(seconds), text)

    async def test_not_a_number(self) -> None:
        with self.assertRaises(ValueError):
            await DurationText().run("soon")


if __name__ == "__main__":
    unittest.main()
