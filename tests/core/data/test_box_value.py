import unittest

from streamer_toolbox.core.data.box_value import same, to_bool, to_list, understand


class TestBoxValue(unittest.TestCase):
    def test_to_list(self) -> None:
        self.assertEqual(to_list(["a", 1]), ["a", 1])
        self.assertEqual(to_list('["hat", "fan"]'), ["hat", "fan"])
        self.assertEqual(to_list(""), [])
        self.assertEqual(to_list(None), [])
        for bad in ("hat", '{"a": 1}', 5):
            with self.assertRaises(ValueError):
                to_list(bad)

    def test_to_bool(self) -> None:
        self.assertFalse(to_bool("False"))
        self.assertFalse(to_bool(" no "))
        self.assertTrue(to_bool("yes"))
        self.assertTrue(to_bool(1))

    def test_same(self) -> None:
        self.assertTrue(same("Fan Blow", "fan blow"))
        self.assertTrue(same("3", 3.0))
        self.assertTrue(same({"x": 1}, {"x": 1}))
        self.assertFalse(same(True, "1"))
        self.assertFalse(same("hat", "fan"))
        self.assertFalse(same("123456789012345678", "123456789012345679"))  # long ids: every digit counts
        self.assertTrue(same("123456789012345678", 123456789012345678))

    def test_understand_keeps_every_digit_of_a_long_whole_number(self) -> None:
        self.assertEqual(understand("123456789012345678"), 123456789012345678)
        self.assertEqual(understand(" -42 "), -42)
        self.assertEqual(understand("1.5"), 1.5)
        self.assertEqual(understand("1e3"), 1000.0)
        self.assertEqual(understand("hat"), "hat")

    def test_understand_keeps_text_that_starts_with_a_zero_or_a_plus(self) -> None:
        self.assertEqual(understand("007"), "007")
        self.assertEqual(understand("+49"), "+49")
        self.assertEqual(understand("-007"), "-007")
        self.assertEqual(understand("0"), 0)
        self.assertEqual(understand("0.5"), 0.5)
        self.assertEqual(understand("-0.5"), -0.5)


if __name__ == "__main__":
    unittest.main()
