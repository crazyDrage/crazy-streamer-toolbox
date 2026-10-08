import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from streamer_toolbox.core.alerts.alert_look import AlertLook
from streamer_toolbox.core.alerts.alert_store import AlertStore


class TestAlertLook(unittest.TestCase):
    def test_the_start_look_tells_the_overlay_nothing(self) -> None:
        self.assertEqual(AlertLook().to_dict(), {})
        self.assertEqual(AlertLook.from_dict(None), AlertLook())

    def test_only_what_differs_is_kept(self) -> None:
        look = AlertLook(text_place="above", animation_in="pop", accent_color=" #ffb347 ")
        saved = look.checked().to_dict()
        self.assertEqual(saved, {"text_place": "above", "animation_in": "pop", "accent_color": "#ffb347"})
        self.assertEqual(AlertLook.from_dict(saved), look.checked())

    def test_an_alert_dragged_to_its_own_spot(self) -> None:
        look = AlertLook(place="free", screen_x=82.5, screen_y=140).checked()
        self.assertEqual(look.to_dict(), {"place": "free", "screen_x": 82.5, "screen_y": 100.0})
        self.assertEqual(AlertLook.from_dict(look.to_dict()), look)

    def test_wrong_values_fall_back_and_numbers_stay_in_range(self) -> None:
        look = AlertLook.from_dict({"text_place": "over", "animation_in": "explode", "animation_out": "pop",
                                    "place": 7, "text_size": "big", "picture_height": 0, "animation_seconds": 60,
                                    "text_x": 20})
        self.assertEqual((look.text_place, look.animation_in, look.animation_out, look.place),
                         ("below", "fade", "fade", "top"))  # pop is only a way in; "over" is a piece's own now
        self.assertEqual((look.text_size, look.picture_height, look.animation_seconds), (44.0, 5.0, 3.0))

    def test_an_alerts_look_is_kept_with_its_rule_and_goes_out_with_the_alert(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "alerts.json"
            store = AlertStore(path)
            look = AlertLook(text_place="above", animation_in="slide_up")
            store.save(replace(store.get("twitch.follow"), look=look))
            again = AlertStore(path)
            self.assertEqual(again.get("twitch.follow").look, look)
            self.assertEqual(again.get("twitch.raid").look, AlertLook())
            self.assertEqual(again.get("twitch.follow").alert_for({"user": "Dragon"}).look, look)


if __name__ == "__main__":
    unittest.main()
