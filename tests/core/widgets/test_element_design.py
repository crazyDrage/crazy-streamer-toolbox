import json
import unittest

from streamer_toolbox.core.widgets.element_design import HTML, ElementDesign
from streamer_toolbox.core.widgets.element_settings import ElementSettings
from streamer_toolbox.core.widgets.widget import Widget


class ElementDesignTest(unittest.TestCase):
    def setUp(self) -> None:
        self.design = ElementDesign.new()
        self.always = self.design.layers()[0][0]

    def test_a_new_one_is_an_element_with_one_layer_always_there(self) -> None:
        widget = Widget("bar", HTML, "", self.design.to_js())
        again = ElementDesign.of(widget)
        self.assertEqual([(0, "Always there")], again.layers())
        self.assertEqual("", again.event_of(0))
        self.assertIsNotNone(ElementSettings.of(widget))  # the Settings tab of the widget page reads it too
        self.assertEqual((1920, 1080), again.canvas())

    def test_code_of_its_own_is_no_design(self) -> None:
        self.assertIsNone(ElementDesign.of(Widget("chat", "<div></div>", "", "console.log(1)")))

    def test_a_text_comes_in_the_middle_with_the_latest_follower(self) -> None:
        name = self.design.add(self.always, "text")
        self.assertEqual("Text", name)
        piece = self.design.piece(self.always, name)
        self.assertEqual("660px", piece["style"]["left"])
        self.assertIn("{session.twitch.follower-latest.name}", self.design.text(self.always, name))
        self.assertNotIn("animation", piece)  # only an alert's pieces come and go

    def test_names_count_up(self) -> None:
        self.assertEqual(["Picture", "Picture 2", "Picture 3"],
                         [self.design.add(self.always, "image") for _ in range(3)])

    def test_an_alert_for_an_event_once(self) -> None:
        layer = self.design.add_alert("follower")
        self.assertEqual(layer, self.design.add_alert("follower"))
        self.assertEqual("follower", self.design.event_of(layer))
        state = self.design.config["configStates"][layer]
        self.assertIn({"==": [{"var": "event.type"}, "follow"]}, state["triggers"][0]["systemCondition"]["and"])
        self.assertEqual([(0, "Always there"), (layer, "Follow alert")], self.design.layers())
        with self.assertRaises(ValueError):
            self.design.add_alert("dance")

    def test_a_sub_alert_leaves_gift_bombs_to_their_own(self) -> None:
        state = self.design.config["configStates"][self.design.add_alert("subscriber")]
        self.assertIn({"!=": [{"var": "event.data.gifted"}, True]}, state["triggers"][0]["systemCondition"]["and"])

    def test_the_layer_always_there_stays(self) -> None:
        with self.assertRaises(ValueError):
            self.design.remove_layer(self.always)
        layer = self.design.add_alert("raid")
        self.design.remove_layer(layer)
        self.assertEqual(1, len(self.design.layers()))

    def test_an_alert_piece_fades_in_stays_and_fades_out(self) -> None:
        layer = self.design.add_alert("cheer")
        name = self.design.add(layer, "text")
        self.assertEqual("{event.data.username} cheered {event.data.amount} bits!", self.design.text(layer, name))
        self.assertEqual({"in": "fade", "in_seconds": 0.5, "delay": 0, "stays": 5, "out": "fade", "out_seconds": 0.5},
                         self.design.animation(layer, name))
        self.design.set_animation(layer, name, **{"in": "slide_down", "stays": 3.5, "out": ""})
        animation = self.design.piece(layer, name)["animation"]
        self.assertEqual("slide_down", animation["enter"]["animationName"])
        self.assertEqual("3.5s", animation["static"]["animationDuration"])
        self.assertNotIn("animationName", animation["exit"])

    def test_streamelements_own_fade_reads_as_a_fade(self) -> None:
        layer = self.design.add_alert("tip")
        name = self.design.add(layer, "image")
        self.design.piece(layer, name)["animation"] = {
            "enter": {"animationName": "fade-in", "animationDuration": "0.35s", "opacity": "0"},
            "static": {"animationDuration": "4.3s"}, "exit": {}}
        self.assertEqual("fade", self.design.animation(layer, name)["in"])
        self.assertEqual("", self.design.animation(layer, name)["out"])
        self.design.set_animation(layer, name, **{"in": "pop"})
        self.assertNotIn("opacity", self.design.piece(layer, name)["animation"]["enter"])

    def test_move_resize_and_style(self) -> None:
        name = self.design.add(self.always, "text")
        self.design.move(self.always, name, 10.456, -20)
        self.design.resize(self.always, name, 300, 24.5)
        self.design.set_style(self.always, name, color="#ff0000", textShadow=None)
        style = self.design.piece(self.always, name)["style"]
        self.assertEqual(("10.46px", "-20px", "300px", "24.5px", "#ff0000"),
                         (style["left"], style["top"], style["width"], style["fontSize"], style["color"]))
        self.assertNotIn("textShadow", style)

    def test_files_set_their_kind(self) -> None:
        name = self.design.add(self.always, "image", "dance.GIF")
        self.assertEqual([{"href": "dance.GIF", "mimeType": "image/gif"}],
                         self.design.piece(self.always, name)["media"])
        self.assertEqual("dance.GIF", self.design.file(self.always, name))
        with self.assertRaises(ValueError):
            self.design.set_file(self.always, name, "song.mp3")
        self.assertEqual({"dance.GIF"}, self.design.files())

    def test_duplicate_rename_restack_remove(self) -> None:
        first = self.design.add(self.always, "text")
        second = self.design.add(self.always, "image")
        twin = self.design.duplicate(self.always, first)
        self.assertEqual(["Text", "Text 2", "Picture"], list(self.design.pieces(self.always)))
        self.assertEqual("680px", self.design.piece(self.always, twin)["style"]["left"])
        self.assertEqual("Title", self.design.rename(self.always, twin, "  Title "))
        with self.assertRaises(ValueError):
            self.design.rename(self.always, "Title", second)
        self.design.restack(self.always, "Title", 5)
        self.assertEqual(["Text", "Picture", "Title"], list(self.design.pieces(self.always)))
        self.design.restack(self.always, "Title", -9)
        self.assertEqual(["Title", "Text", "Picture"], list(self.design.pieces(self.always)))
        self.design.remove(self.always, "Title")
        self.assertEqual(["Text", "Picture"], list(self.design.pieces(self.always)))

    def test_a_reaction_on_follows(self) -> None:
        name = self.design.add(self.always, "image")
        self.assertEqual([], self.design.reaction(self.always, name)["events"])
        self.design.set_reaction(self.always, name, ["follower", "nonsense"], "shake", 1.2)
        self.assertEqual({"events": ["follower"], "animation": "shake", "seconds": 1.2},
                         self.design.reaction(self.always, name))
        self.assertEqual({"follower"}, self.design.events())
        self.design.set_reaction(self.always, name, [])
        self.assertNotIn("toolbox", self.design.piece(self.always, name))
        self.design.add_alert("raid")
        self.assertEqual({"raid"}, self.design.events())

    def test_a_copy_is_its_own(self) -> None:
        copy = self.design.copy()
        self.design.add(self.always, "text")
        self.assertEqual({}, copy.pieces(0))

    def test_the_js_part_reads_back(self) -> None:
        self.design.add(self.always, "text")
        code = self.design.to_js()
        self.assertTrue(code.startswith("TOOLBOX_ELEMENT.show("))
        self.assertEqual(self.design.config, json.loads(code[len("TOOLBOX_ELEMENT.show("):code.rindex(")")]))

    def test_a_saved_design_plays_the_top_variation_first(self) -> None:
        self.assertNotIn("toolbox", self.design.config)
        self.design.to_js()
        self.assertEqual({"top_first": True}, self.design.config["toolbox"])


if __name__ == "__main__":
    unittest.main()
