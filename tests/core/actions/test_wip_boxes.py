import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.connections.vtube_studio.vts_position_store import VtsPositionStore
from streamer_toolbox.connections.vts_connection import VtsConnection
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.wip_boxes import WIP_BOXES, shows_wip


class TestWipBoxes(unittest.TestCase):
    def test_only_show_true_in_the_wip_table_shows_them(self) -> None:
        self.assertTrue(shows_wip({"wip": {"show": True}}))
        for tables in ({}, {"wip": {}}, {"wip": {"show": False}}, {"wip": {"show": "yes"}}, {"wip": True}):
            self.assertFalse(shows_wip(tables), tables)

    def test_every_parked_box_exists_and_has_a_reason(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            actions = ActionRegistry()
            VtsConnection({}, Path(folder) / "vts_token.txt",
                          VtsPositionStore(Path(folder) / "vts_positions.toml")).add_actions(actions)
            for name, reason in WIP_BOXES.items():
                self.assertIn(name, actions)  # a renamed or removed box must leave this list too
                self.assertTrue(reason.strip(), name)

    def test_parked_pin_boxes_are_not_offered_but_the_other_item_boxes_are(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            actions = ActionRegistry()
            VtsConnection({}, Path(folder) / "vts_token.txt",
                          VtsPositionStore(Path(folder) / "vts_positions.toml")).add_actions(actions)
            actions.park(WIP_BOXES)
            offered = {a.name for a in actions.all(include_flow_only=True)}
        self.assertFalse(offered & set(WIP_BOXES))
        self.assertLessEqual({"vts.load_item", "vts.move_item", "vts.remove_items"}, offered)


if __name__ == "__main__":
    unittest.main()
