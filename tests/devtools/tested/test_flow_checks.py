import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.devtools.tested.flow_checks import FlowChecks

FLOW = '''label = "Warudo camera test"
wires = [{from = "t1", port = "out", to = "n1"}]

[[triggers]]
kind = "warudo.message"
id = "t1"
box = [20, 40]
type = "camera"

[[nodes]]
id = "n1"
action = "var.set"
box = [320, 40]
params = {name = "x", value = "1"}

[[nodes]]
id = "n2"
action = "warudo.send"
box = [620, 40]
params = {action = "wave"}
'''


class TestFlowChecks(unittest.TestCase):
    """His named flows → the rows of every box and trigger in them."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        folder = Path(self._dir.name)
        (folder / "warudo_camera.toml").write_text(FLOW, encoding="utf-8")
        (folder / "other.toml").write_text(FLOW.replace("Warudo camera test", "Other")
                                           .replace("warudo.send", "obs.set_scene"), encoding="utf-8")
        self.checks = FlowChecks(folder)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_flows_are_found_by_file_name_or_label_in_any_case(self) -> None:
        flows, missing = self.checks.find(["warudo_camera", "OTHER", "nope", "Warudo Camera Test"])
        self.assertEqual(["Warudo camera test", "Other"], [f.label for f in flows])
        self.assertEqual(["nope"], missing)

    def test_every_box_and_trigger_with_the_flows_it_is_in(self) -> None:
        flows, _ = self.checks.find(["warudo_camera", "other"])
        self.assertEqual({"trigger:warudo.message": ["Warudo camera test", "Other"],
                          "box:var.set": ["Warudo camera test", "Other"],
                          "box:warudo.send": ["Warudo camera test"],
                          "box:obs.set_scene": ["Other"]}, FlowChecks.keys(flows))


if __name__ == "__main__":
    unittest.main()
