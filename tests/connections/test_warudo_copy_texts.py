import json
import unittest

from streamer_toolbox.connections.warudo.warudo_copy_texts import (ASSET_TYPE, ON_ACTION, PLACEHOLDER, SET_PROPERTY,
                                                                    WarudoCopyTexts, connect_action)

ADDRESS = "ws://localhost:8850/connections/warudo/in/camera?key=abc"


class TestWarudoCopyTexts(unittest.TestCase):
    """Copy asset / Copy blueprint: his exported shape, the blueprint pointing at the asset of the same type."""

    def setUp(self) -> None:
        self.texts = WarudoCopyTexts()
        self.asset = json.loads(self.texts.asset("camera", ADDRESS))
        self.blueprint = json.loads(self.texts.blueprint("camera"))

    def test_the_asset_carries_the_address(self) -> None:
        self.assertEqual(ASSET_TYPE, self.asset["typeId"])
        self.assertEqual(ADDRESS, json.loads(self.asset["dataInputs"]["WSAddr"]["value"]))
        self.assertEqual("toolbox_input_camera", self.asset["name"])

    def test_the_blueprint_sets_the_placeholder_then_the_address_that_came(self) -> None:
        nodes = self.blueprint["nodes"]
        by_type = {}
        for node in nodes.values():
            by_type.setdefault(node["typeId"], []).append(node)
        on_action = by_type[ON_ACTION][0]
        self.assertEqual(connect_action("camera"), json.loads(on_action["dataInputs"]["Action"]["value"]))
        flow = [(c["outputNode"], c["inputNode"]) for c in self.blueprint["flowConnections"]]
        first = next(target for source, target in flow if source == on_action["id"])
        second = next(target for source, target in flow if source == first)
        self.assertEqual(PLACEHOLDER, json.loads(nodes[first]["dataInputs"]["TargetValue"]["value"]))
        self.assertEqual([{"outputNode": on_action["id"], "inputNode": second, "outputPort": "StringData",
                           "inputPort": "TargetValue"}], self.blueprint["dataConnections"])
        for node in by_type[SET_PROPERTY]:
            asset = json.loads(node["dataInputs"]["Asset"]["value"])
            self.assertEqual(self.asset["id"], asset["id"])  # finds the asset copied for the same type
            self.assertEqual("WSAddr", json.loads(node["dataInputs"]["DataPath"]["value"]))

    def test_each_type_has_its_own_ids_and_no_key_is_in_the_blueprint(self) -> None:
        other = json.loads(self.texts.asset("default", ADDRESS))
        self.assertNotEqual(self.asset["id"], other["id"])
        self.assertEqual(self.asset["id"], json.loads(self.texts.asset("camera", "x"))["id"])
        self.assertNotIn("key=", self.texts.blueprint("camera"))


if __name__ == "__main__":
    unittest.main()
