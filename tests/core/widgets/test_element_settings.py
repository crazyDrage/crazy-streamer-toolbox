import json
import unittest

from streamer_toolbox.core.widgets.element_settings import ElementSettings
from streamer_toolbox.core.widgets.streamelements_elements import HTML, JS
from streamer_toolbox.core.widgets.widget import Widget

FADE = {"enter": {"animationDuration": "0.35s"}, "static": {"animationDuration": "4.3s"}, "exit": {}}
CONFIG = {"boundingBox": {"width": 1920, "height": 1080}, "configStates": [
    {"referenceId": "background", "displayName": "Background", "categoryId": None, "settings": {"compositeFields": {
        "Back": {"type": "video", "volume": 1, "playbackRate": 1, "style": {"left": "0px", "top": "0px"},
                 "animation": {"enter": {}, "static": {}, "exit": {}}},
        "Label": {"type": "text", "text": [{"content": "LATEST: {session.twitch.follower-latest.name}"}],
                  "style": {"fontFamily": "Teko", "fontSize": "20px", "color": "#ffffff", "left": "580px",
                            "top": "1016.5px"},
                  "highlightedStyle": {"color": "#fbc9e9"}, "animation": {"static": {"animationDuration": "3s"}}},
        "Ticker": {"type": "latestTicker", "text": [{"content": "{session.twitch.tip-latest.name} /"}],
                   "style": {"width": "auto"}, "animation": {"static": {"animationDuration": "8s"}}}}}},
    {"referenceId": "platformEvents", "displayName": "Default", "categoryId": "follower",
     "settings": {"compositeFields": {
         "Alert sound": {"type": "audio", "volume": 0.5, "delaySeconds": 0},
         "Text": {"type": "text", "text": [{"content": "{event.data.username}\njust followed"}],
                  "style": {"fontSize": "28px", "left": "1459.16px"}, "animation": FADE}}}},
    {"referenceId": "x", "displayName": "Big tip", "categoryId": "tip", "settings": {}}]}


class ElementSettingsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.widget = Widget("ended", HTML, "", JS.format(config=json.dumps(CONFIG, indent=1)))
        self.settings = ElementSettings.of(self.widget)

    def test_only_an_imported_element_has_them(self) -> None:
        self.assertIsNotNone(self.settings)
        self.assertIsNone(ElementSettings.of(Widget("chat", "<div></div>", "", "let a = 1;")))
        self.assertIsNone(ElementSettings.of(Widget("ended", HTML, "", "TOOLBOX_ELEMENT.show({broken);")))
        self.assertEqual(ElementSettings.of(Widget("ended", HTML, "", self.settings.to_js())).fields(),
                         self.settings.fields())

    def test_the_fields_of_each_piece(self) -> None:
        fields = self.settings.fields()
        self.assertEqual({key: (spec["type"], spec["value"]) for key, spec in fields.items()}, {
            "0/Back/volume": ("slider", 100), "0/Back/left": ("number", 0), "0/Back/top": ("number", 0),
            "0/Label/text": ("textarea", "LATEST: {session.twitch.follower-latest.name}"),
            "0/Label/size": ("number", 20), "0/Label/color": ("colorpicker", "#ffffff"),
            "0/Label/highlight": ("colorpicker", "#fbc9e9"),
            "0/Label/left": ("number", 580), "0/Label/top": ("number", 1016.5),  # always there: no "stays"
            "0/Ticker/text": ("textarea", "{session.twitch.tip-latest.name} /"), "0/Ticker/stays": ("number", 8),
            "1/Alert sound/volume": ("slider", 50), "1/Alert sound/delay": ("number", 0),
            "1/Text/text": ("textarea", "{event.data.username}\njust followed"), "1/Text/size": ("number", 28),
            "1/Text/stays": ("number", 4.3), "1/Text/left": ("number", 1459.16)})
        self.assertEqual(fields["0/Label/text"]["group"], "Background · Label")
        self.assertEqual(fields["1/Text/text"]["group"], "Follow alert · Text")
        self.assertEqual(fields["0/Ticker/stays"]["label"], "One round takes (seconds)")

    def test_changed_values_are_written_and_the_rest_is_left_alone(self) -> None:
        same = self.settings.with_values({key: spec["value"] for key, spec in self.settings.fields().items()})
        self.assertEqual(json.loads(same.to_js()[len("TOOLBOX_ELEMENT.show("):-2]), CONFIG)  # "1459.16px" as it was

        changed = self.settings.with_values({
            "0/Label/text": "NEWEST: {session.twitch.follower-latest.name}", "0/Label/size": 24.0,
            "0/Label/color": "#ff0000", "0/Label/highlight": "#00ff00", "0/Label/top": 990,
            "1/Alert sound/volume": 80, "1/Alert sound/delay": 1.5, "1/Text/stays": 6, "0/Ticker/stays": None,
            "9/Nothing/text": "ignored"})
        config = json.loads(changed.to_js()[len("TOOLBOX_ELEMENT.show("):-2])
        label = config["configStates"][0]["settings"]["compositeFields"]["Label"]
        self.assertEqual(label["text"], [{"content": "NEWEST: {session.twitch.follower-latest.name}"}])
        self.assertEqual(label["style"], {"fontFamily": "Teko", "fontSize": "24px", "color": "#ff0000",
                                          "left": "580px", "top": "990px"})
        self.assertEqual(label["highlightedStyle"], {"color": "#00ff00"})
        alert = config["configStates"][1]["settings"]["compositeFields"]
        self.assertEqual(alert["Alert sound"], {"type": "audio", "volume": 0.8, "delaySeconds": 1.5})
        self.assertEqual(alert["Text"]["animation"]["static"], {"animationDuration": "6s"})
        self.assertEqual(alert["Text"]["animation"]["enter"], {"animationDuration": "0.35s"})
        self.assertEqual(self.settings.fields()["0/Label/size"]["value"], 20)  # the old one is not touched
