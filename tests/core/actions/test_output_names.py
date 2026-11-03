import unittest

from streamer_toolbox.core.actions.output_names import names_in


class TestOutputNames(unittest.TestCase):
    def test_commas_or_lines_spaces_left_out_each_once(self) -> None:
        self.assertEqual(["text", "count", "my value"], names_in(" text, count,\nmy value , text,, "))

    def test_nothing_typed(self) -> None:
        self.assertEqual([], names_in(""))
        self.assertEqual([], names_in(None))


if __name__ == "__main__":
    unittest.main()
