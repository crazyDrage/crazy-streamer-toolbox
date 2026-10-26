import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.assembly.own_boxes import OwnBoxes
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.media.mp4_header_probe import Mp4HeaderProbe
from streamer_toolbox.core.variables.variable_store import VariableStore
from tests.fakes.fake_confirm_service import FakeConfirmService
from tests.fakes.fake_message_service import FakeMessageService


class TestOwnBoxes(unittest.TestCase):
    def test_every_group_adds_its_boxes_with_texts(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            actions = ActionRegistry()
            OwnBoxes(VariableStore(Path(folder) / "variables"), Mp4HeaderProbe(), FakeMessageService(),
                     FakeConfirmService(True), None).add_to(actions)
        boxes = actions.all(include_flow_only=True)
        self.assertEqual([b.name for b in boxes if not b.label or not b.description], [])
        categories = {b.name.split(".")[0] for b in boxes}
        self.assertLessEqual({"file", "list", "json", "object", "text", "sound"}, categories)


if __name__ == "__main__":
    unittest.main()
