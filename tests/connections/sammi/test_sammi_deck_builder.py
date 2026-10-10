import json
import random
import unittest
from datetime import datetime

from streamer_toolbox.connections.sammi.sammi_deck_builder import HTTP_REQUEST, SammiDeckBuilder

ACTIONS = [
    {"name": "hello.greet", "label": "Say hello", "description": "",
     "params": [{"name": "name", "required": False}]},
    {"name": "obs.fit_raid_clip", "description": "", "params": [{"name": "video_path", "required": True}]},
]
# every button key in crazyDrage's SAMMI 2025.3.1 exports
EXPORTED_KEYS = {
    "border", "border_color", "button_duration", "button_id", "color", "command_list", "deck", "font_color",
    "font_shadow", "functions", "group_id", "height", "image", "init_variable", "is_transparent", "overlappable",
    "payload", "persistent", "press_type", "queueable", "release_duration", "release_list", "stretch",
    "switch_deck", "text", "triggers", "width", "x", "y",
}


class TestSammiDeckBuilder(unittest.TestCase):
    def setUp(self) -> None:
        builder = SammiDeckBuilder("http://127.0.0.1:8850/", now=datetime(2026, 9, 28, 12, 0, 0, 123000),
                                   rng=random.Random(1))
        self.file = builder.build(ACTIONS)
        self.deck = json.loads(self.file["deck_data"])
        self.buttons = self.deck["button_list"]

    def test_file_has_the_paste_deck_wrapper(self) -> None:
        self.assertEqual(set(self.file), {"deck_data", "unique_id", "include_image"})
        self.assertEqual(self.file["unique_id"], self.deck["unique_id"])
        self.assertTrue(self.file["unique_id"].startswith("20260928120000123"))
        self.assertEqual(self.deck["deck_name"], "toolbox")

    def test_one_http_post_button_per_action(self) -> None:
        self.assertEqual([b["button_id"] for b in self.buttons], ["tb_hello_greet", "tb_obs_fit_raid_clip"])
        self.assertEqual([b["text"] for b in self.buttons], ["Say hello", "obs.fit_raid_clip"])
        command = self.buttons[0]["command_list"][0]
        self.assertEqual((command["cmd"], command["b0"], command["b1"], command["b3"]),
                         (HTTP_REQUEST, "http://127.0.0.1:8850/action/hello.greet", "POST", ""))

    def test_required_params_become_sammi_variables(self) -> None:
        body = self.buttons[1]["command_list"][0]["b3"]
        self.assertEqual(json.loads(body), {"video_path": "/$video_path$/"})

    def test_buttons_have_every_key_sammi_exports(self) -> None:
        self.assertEqual(set(self.buttons[0]), EXPORTED_KEYS)

    def test_buttons_stay_inside_the_deck(self) -> None:
        many = SammiDeckBuilder("http://x").build([{"name": f"a{i}", "params": []} for i in range(50)])
        for b in json.loads(many["deck_data"])["button_list"]:
            self.assertLessEqual(b["x"] + b["width"], 1.0)
            self.assertLessEqual(b["y"] + b["height"], 1.0 + 1e-9)


if __name__ == "__main__":
    unittest.main()
