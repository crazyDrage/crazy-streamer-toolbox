import unittest

from streamer_toolbox.gui.components.flow_editor.param_input import _sorted, field_label


class TestParamInputChoices(unittest.TestCase):
    def test_a_short_list_keeps_its_order_and_a_long_one_goes_a_to_z(self) -> None:
        wait = {"nothing": "Nothing", "restart": "Start the wait over", "add": "Add the time again"}
        self.assertEqual(list(_sorted(wait, [])), ["nothing", "restart", "add"])
        self.assertEqual(list(_sorted(["+", "-", "*", "/"], ["%"])), ["+", "-", "*", "/", "%"])
        scenes = [f"scene {c}" for c in "zyxwvutsrqponm"]
        self.assertEqual(list(_sorted(scenes, []))[:2], ["scene m", "scene n"])

    def test_field_names_read_as_words(self) -> None:
        self.assertEqual(field_label("if_started_again"), "If started again")
        self.assertEqual(field_label("case_1"), "Case 1")


if __name__ == "__main__":
    unittest.main()
