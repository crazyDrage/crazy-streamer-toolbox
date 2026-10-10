import unittest

from streamer_toolbox.gui.components.flow_editor.wire_matcher import WireMatcher

SOURCES = {"${box.start.scene}": "Start · scene", "${box.start.source}": "Start · source",
           "${box.n2.width}": "2 · Split · width", "${box.n2.height}": "2 · Split · height",
           "${box.n5.height}": "5 · Set source size · height", "${box.n1}": "1 · Video info"}


class TestWireMatcher(unittest.TestCase):
    def test_same_names_are_offered_clear_ones_ticked(self) -> None:
        rows = WireMatcher.candidates(["scene", "Source", "width", "height", "scale"], SOURCES,
                                      {"scene": "", "Source": "sound_alert", "width": "${box}",
                                       "height": "${box.n5.height}"})
        self.assertEqual([(field, list(matches), pick) for field, matches, pick in rows], [
            ("scene", ["${box.start.scene}"], "${box.start.scene}"),        # empty: ticked
            ("Source", ["${box.start.source}"], None),                     # typed already: offered, not ticked
            ("width", ["${box.n2.width}"], "${box.n2.width}"),             # waits for a wire: ticked
            ("height", ["${box.n2.height}", "${box.n5.height}"], "${box.n5.height}")])  # keeps its wire

    def test_names_ignore_case_and_underscores(self) -> None:
        self.assertEqual(WireMatcher.key("Button_ID"), WireMatcher.key("button id"))
        rows = WireMatcher.candidates(["button_id"], {"${box.start.buttonId}": "Start · buttonId"}, {})
        self.assertEqual(rows[0][2], "${box.start.buttonId}")

    def test_a_result_dropped_by_name_fills_the_matching_empty_fields(self) -> None:
        chosen, kept = WireMatcher.by_name(
            ["scene", "source", "width", "height", "scale"], "n1", ["width", "height", "seconds", "orientation"],
            {"scene": "toolbox_test", "width": "${box}", "height": "${box.n4.height}"})
        self.assertEqual(chosen, {"width": "${box.n1.width}"})  # scale has no key; seconds no field
        self.assertEqual(kept, {"height": "${box.n4.height}"})  # another wire brings a height: stays

    def test_dropping_the_same_result_again_changes_nothing(self) -> None:
        chosen, kept = WireMatcher.by_name(["Width"], "n1", ["width"], {"Width": "${box.n1.width}"})
        self.assertEqual((chosen, kept), ({"Width": "${box.n1.width}"}, {}))

    def test_as_value_fills_the_first_free_field(self) -> None:
        self.assertEqual(WireMatcher.as_value(["left", "op", "right"], "n2", "", {"op": "=="}),
                         {"left": "${box.n2}"})
        self.assertEqual(WireMatcher.as_value(["left", "op", "right"], "n2", "x", {"left": "a", "op": "=="}),
                         {"right": "${box.n2.x}"})
        self.assertEqual(WireMatcher.as_value(["left"], "n2", "", {"left": "taken"}), {})
