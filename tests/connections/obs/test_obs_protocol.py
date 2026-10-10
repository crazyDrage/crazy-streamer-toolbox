import json
import unittest

from streamer_toolbox.connections.obs.obs_protocol import ObsProtocol


class TestObsProtocol(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = ObsProtocol()  # the real file

    def test_template_has_what_the_request_needs(self) -> None:
        data = json.loads(self.protocol.template("SetSceneItemEnabled")["data"])
        self.assertEqual(data, {"sceneName": "", "sceneItemId": 0, "sceneItemEnabled": True})
        data = json.loads(self.protocol.template("CreateInput")["data"])
        self.assertEqual(data, {"sceneName": "", "inputName": "", "inputKind": ""})
        self.assertEqual(self.protocol.template("GetStats"), {})
        self.assertEqual(self.protocol.template("NoSuchRequest"), {})

    def test_hint_names_the_fields(self) -> None:
        hint = self.protocol.hint({"request": "SetInputAudioMonitorType"})
        self.assertIn("monitorType (text)", hint)
        self.assertIn("Needs:", hint)
        self.assertTrue(self.protocol.hint({"request": "GetStats"}).endswith("No data needed."))
        self.assertIn("pick a request", self.protocol.hint({}))

    def test_by_category_only_what_this_obs_has(self) -> None:
        groups = self.protocol.by_category(["GetSceneList", "GetStats", "SomeNewRequest"])
        self.assertEqual(groups, {"General": {"GetStats": "GetStats"}, "Other": {"SomeNewRequest": "SomeNewRequest"},
                                  "Scenes": {"GetSceneList": "GetSceneList"}})
        self.assertIn("Media inputs", self.protocol.by_category())


if __name__ == "__main__":
    unittest.main()
