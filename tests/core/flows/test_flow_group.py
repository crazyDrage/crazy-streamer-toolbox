import unittest

from streamer_toolbox.core.flows.flow_group import FlowGroup
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft


class TestFlowGroup(unittest.TestCase):
    """His round 83: a box belongs to a group when its middle is inside the area."""

    def test_holds_a_point_inside_the_open_area(self) -> None:
        group = FlowGroup("g1", box=(100.0, 100.0), size=(200.0, 100.0))
        self.assertTrue(group.holds((150.0, 150.0)))
        self.assertTrue(group.holds((300.0, 200.0)))  # on the edge
        self.assertFalse(group.holds((301.0, 150.0)))
        self.assertFalse(group.holds((150.0, 99.0)))

    def test_a_draft_numbers_its_groups(self) -> None:
        draft = FlowDraft("f", "F")
        self.assertEqual(draft.add_group((10.0, 20.0)).id, "g1")
        self.assertEqual(draft.add_group((0.0, 0.0)).id, "g2")
        self.assertEqual(draft.group("g1").box, (10.0, 20.0))
        self.assertEqual(draft.to_flow().groups, tuple(draft.groups))
        self.assertEqual(FlowDraft.from_flow(draft.to_flow()).groups, draft.groups)


if __name__ == "__main__":
    unittest.main()
