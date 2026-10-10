import unittest
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.flows.debug_actions import DEBUG_BOX, DebugActions


class TestDebugActions(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.shown: list[tuple[str, str, bool, Any]] = []

    def _show(self, source: str, what: str, ok: bool, text: Any) -> None:
        self.shown.append((source, what, ok, text))

    async def test_it_shows_the_value_with_its_kind_and_gives_it_on_unchanged(self) -> None:
        debug = DebugActions(self._show).debug
        self.assertEqual(await debug("5"), "5")
        self.assertEqual(await debug(5, "after the split"), 5)
        self.assertEqual(await debug({"a": [1, True]}), {"a": [1, True]})
        self.assertEqual(self.shown, [("Debug", "Debug", True, "'5' (str)"),
                                      ("Debug", "after the split", True, "5 (int)"),
                                      ("Debug", "Debug", True, "{'a': [1, True]} (dict)")])

    async def test_without_a_place_to_show_it_still_gives_the_value_on(self) -> None:
        self.assertEqual(await DebugActions().debug(0.5), 0.5)

    async def test_it_is_a_box_of_the_flow_group_whose_typed_value_keeps_its_kind(self) -> None:
        actions = ActionRegistry()
        DebugActions().add_to(actions)
        box = actions.get(DEBUG_BOX)
        self.assertEqual((box.label, box.group, box.typed), ("Debug", "Flow", ("value",)))


if __name__ == "__main__":
    unittest.main()
