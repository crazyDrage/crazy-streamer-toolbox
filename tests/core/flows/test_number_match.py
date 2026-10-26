import unittest

from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.number_match import compare_of, fits_number, to_compare


class TestNumberMatch(unittest.TestCase):
    def _fires(self, how: str, number, *rates: int) -> list[bool]:
        trigger = FlowTrigger("heartrate", {"bpm": to_compare(how, number)})
        return [trigger.matches("heartrate", {"bpm": bpm, "source": "pulsoid"}) for bpm in rates]

    def test_any_higher_lower_and_equal(self) -> None:
        self.assertEqual(self._fires("", 0, 50, 120, 200), [True, True, True])
        self.assertEqual(self._fires(">", 120, 119, 120, 121), [False, False, True])
        self.assertEqual(self._fires("<", 60, 59, 60, 61), [True, False, False])
        self.assertEqual(self._fires("=", 100, 99, 100, 101), [False, True, False])

    def test_rises_above_and_falls_below_start_once_when_it_is_crossed(self) -> None:
        def fires(how: str, *rates: int) -> list[bool]:
            trigger = FlowTrigger("heartrate", {"bpm": to_compare(how, 120)})
            return [trigger.matches("heartrate", {"bpm": now, "previous_bpm": before, "source": "pulsoid"})
                    for before, now in zip((0,) + rates, rates)]

        # 121, 123, 125: "higher than" starts three times, "rises above" once
        self.assertEqual(fires(">", 110, 121, 123, 125), [False, True, True, True])
        self.assertEqual(fires(">>", 110, 121, 123, 125, 118, 120, 130),
                         [False, True, False, False, False, False, True])
        self.assertEqual(fires("<<", 130, 121, 119, 115, 125, 110), [False, False, True, False, False, True])
        self.assertEqual(fires(">>", 130), [True])  # the first beat counts from 0
        no_before = FlowTrigger("heartrate", {"bpm": ">>120"})
        self.assertFalse(no_before.matches("heartrate", {"bpm": 130, "source": "pulsoid"}))

    def test_what_is_saved_and_read_back(self) -> None:
        self.assertEqual([to_compare(how, 120) for how in ("", ">", "<", "=", ">>", "<<", "?")],
                         ["*", ">120", "<120", "=120", ">>120", "<<120", "*"])
        self.assertEqual(compare_of(">>120"), (">>", 120.0))
        self.assertEqual(to_compare(">", "99.5"), ">99.5")
        self.assertEqual(to_compare(">", None), ">0")  # an emptied number field
        self.assertEqual((compare_of(">120"), compare_of(" < 60 "), compare_of("=99.5")),
                         ((">", 120.0), ("<", 60.0), ("=", 99.5)))
        for no_comparison in ("*", "", "pulsoid", ">", "120", ">fast"):
            self.assertIsNone(compare_of(no_comparison), no_comparison)

    def test_only_a_number_in_the_event_is_compared(self) -> None:
        self.assertIsNone(fits_number(">3", ">2"))  # a text stays a text
        self.assertIsNone(fits_number(True, ">0"))
        self.assertIsNone(fits_number(120, "*"))
        chat = FlowTrigger("chat", {"message": ">3"})  # a chat message that says ">3" still matches as text
        self.assertTrue(chat.matches("chat", {"message": ">3"}))
        self.assertFalse(chat.matches("chat", {"message": "5"}))
        older = FlowTrigger("heartrate", {"source": "*"})  # a trigger saved before: still every change
        self.assertTrue(older.matches("heartrate", {"bpm": 70, "source": "pulsoid"}))


if __name__ == "__main__":
    unittest.main()
