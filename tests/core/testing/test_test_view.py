import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.testing.test_gate import TestGate
from streamer_toolbox.core.testing.test_item import BOX, CONNECTION, TOOL, TRIGGER, TestItem
from streamer_toolbox.core.testing.test_list import CHECKS, TestList
from streamer_toolbox.core.testing.test_view import NORMAL, TESTING, TestView
from streamer_toolbox.gui.components.flow_editor.trigger_kinds import offered_triggers

ITEMS = [TestItem(BOX, "obs.set_scene", "Set scene", "OBS", file="flows/boxes/obs/general"),
         TestItem(BOX, "obs.mute", "Mute", "OBS", file="flows/boxes/obs/general"),
         TestItem(BOX, "obs.record", "Record", "OBS", file="flows/boxes/obs/general"),
         TestItem(BOX, "logic.value", "Value", "Logic", file="flows/boxes/logic/flow"),
         TestItem(BOX, "logic.debug", "Debug", "Logic", file="flows/boxes/logic/flow"),
         TestItem(TRIGGER, "timer", "Timer", "Toolbox", file="flows/triggers/toolbox"),
         TestItem(TRIGGER, "follow", "Follow", "Any platform", file="flows/triggers/any_platform"),
         TestItem(TOOL, "points", "Points", file="tools/points"),
         TestItem(CONNECTION, "obs", "OBS", file="connections/obs"),
         TestItem(CONNECTION, "rumble", "Rumble", file="connections/rumble")]
DONE = ("box:obs.set_scene", "box:logic.value", "box:logic.debug", "trigger:timer")  # all three checks
WORKS = ("box:obs.mute", "tool:points", "connection:obs")  # works only


class TestTestView(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        tested = TestList(Path(self._dir.name) / "tested")
        tested.sync(ITEMS)
        for key in DONE:
            for check in CHECKS:
                tested.set_check(key, check, True)
        for key in WORKS:
            tested.set_check(key, "works", True)
        self.actions = ActionRegistry()

        async def noop() -> None:
            return None

        for name in ("obs.set_scene", "obs.mute", "obs.record", "logic.value", "logic.debug",
                     "flow.my_flow"):
            self.actions.add(name, noop)
        TestGate(tested, False).apply(self.actions, [], lambda: ITEMS)
        self.choice: dict = {}
        self.view = TestView(tested, self.choice)

    def _boxes(self) -> list[str]:
        return [a.name for a in self.actions.all() if self.view.shows_box(a)]

    def test_a_box_carries_his_three_checks(self) -> None:
        mute = self.actions.get("obs.mute")
        self.assertEqual((mute.is_tested, mute.is_understandable, mute.is_usable), (True, False, False))
        scene = self.actions.get("obs.set_scene")
        self.assertEqual((scene.is_tested, scene.is_understandable, scene.is_usable), (True, True, True))
        self.assertFalse(self.actions.get("obs.record").is_tested)

    def test_at_first_it_shows_what_works_and_his_own_flows(self) -> None:
        self.assertEqual((self.view.mode, self.view.may_not), (NORMAL, ("understandable", "usable")))
        self.assertEqual(self._boxes(), ["flow.my_flow", "logic.debug", "logic.value", "obs.mute", "obs.set_scene"])
        self.assertTrue(self.view.shows_key("trigger:timer"))
        self.assertFalse(self.view.shows_key("trigger:follow"))
        self.assertTrue(self.view.shows_key("tool:points"))
        self.assertEqual(self.view.shown(ITEMS), {BOX: (4, 5), TRIGGER: (1, 2), TOOL: (1, 1), CONNECTION: (1, 2)})
        self.assertTrue(self.view.shows_key("connection:obs"))
        self.assertFalse(self.view.shows_key("connection:rumble"))

    def test_a_tick_lets_in_what_misses_that_check(self) -> None:
        self.view.let_in("usable", False)  # may only miss Understandable: Mute also misses Usable
        self.assertEqual(self.view.may_not, ("understandable",))
        self.assertEqual(self._boxes(), ["flow.my_flow", "logic.debug", "logic.value", "obs.set_scene"])
        self.assertFalse(self.view.shows_key("tool:points"))
        self.view.let_in("usable", True)
        self.view.let_in("works", True)
        self.assertEqual(len(self._boxes()), 6)
        with self.assertRaises(ValueError):
            self.view.let_in("pretty", True)

    def test_every_tick_shows_everything_and_no_tick_only_what_is_done(self) -> None:
        self.view.let_in("works", True)
        self.assertEqual(len(self._boxes()), 6)
        self.assertTrue(self.view.shows_key("trigger:follow"))
        self.assertEqual(self.view.why(), "")
        for check in CHECKS:
            self.view.let_in(check, False)
        self.assertEqual(self._boxes(), ["flow.my_flow", "logic.debug", "logic.value", "obs.set_scene"])
        self.assertEqual(self.view.why(), "not tested yet")

    def test_testing_shows_only_what_a_tick_names_and_keeps_the_debug_and_value_box(self) -> None:
        self.view.set_mode(TESTING)
        self.view.let_in("understandable", False)
        self.view.let_in("usable", False)
        self.view.let_in("works", True)  # May not work: only what doesn't work yet
        self.assertEqual(self._boxes(), ["flow.my_flow", "logic.debug", "logic.value", "obs.record"])
        self.assertFalse(self.view.shows_key("tool:points"))
        self.assertTrue(self.view.shows_key("trigger:follow"))
        self.assertEqual(self.view.shown(ITEMS)[CONNECTION], (1, 2))
        self.view.let_in("usable", True)  # and May not be usable: what misses one of the two
        self.assertEqual(self._boxes(), ["flow.my_flow", "logic.debug", "logic.value", "obs.mute", "obs.record"])
        self.assertTrue(self.view.shows_key("tool:points"))
        self.assertFalse(self.view.shows_key("trigger:timer"))

    def test_testing_without_a_tick_shows_what_misses_any_of_the_three(self) -> None:
        self.view.set_mode(TESTING)
        for check in CHECKS:
            self.view.let_in(check, False)
        self.assertEqual(self._boxes(), ["flow.my_flow", "logic.debug", "logic.value", "obs.mute", "obs.record"])
        self.assertFalse(self.view.shows_key("trigger:timer"))
        self.assertEqual(self.view.shown(ITEMS)[BOX], (4, 5))
        self.assertEqual(self.view.shown(ITEMS)[CONNECTION], (2, 2))  # neither has all three checks

    def test_disconnected_is_off_at_first_and_kept(self) -> None:
        self.assertFalse(self.view.disconnected)
        self.view.set_disconnected(True)
        self.assertTrue(TestView(TestList(Path(self._dir.name) / "tested"), self.choice).disconnected)

    def test_the_choice_of_before_still_shows_the_same(self) -> None:
        self.choice.update({"test_view_mode": "everything", "test_view_needed": ["works", "usable"]})
        self.assertEqual((self.view.mode, self.view.may_not), (NORMAL, tuple(CHECKS)))
        self.assertEqual(len(self._boxes()), 6)
        self.choice.update({"test_view_mode": "tested", "test_view_needed": ["works", "usable"]})
        self.assertEqual((self.view.mode, self.view.may_not), (NORMAL, ("understandable",)))  # had to work, be usable
        self.assertEqual(self._boxes(), ["flow.my_flow", "logic.debug", "logic.value", "obs.set_scene"])
        self.choice.update({"test_view_mode": "testing", "test_view_needed": ["works"]})  # hid what works
        self.assertEqual((self.view.mode, self.view.may_not), (TESTING, ("works",)))
        self.assertEqual(self._boxes(), ["flow.my_flow", "logic.debug", "logic.value", "obs.record"])
        self.view.let_in("usable", True)  # from now on kept under the new name
        self.assertEqual(self.choice["test_view_may_not"], ["works", "usable"])

    def test_the_add_trigger_window_offers_only_the_shown_triggers(self) -> None:
        self.assertEqual(list(offered_triggers(None, self.view)), ["timer"])
        self.view.let_in("works", True)
        self.assertEqual(offered_triggers(None, self.view), offered_triggers(None))

    def test_the_choice_is_kept_and_a_wrong_one_falls_back(self) -> None:
        self.view.set_mode(TESTING)
        self.assertEqual(TestView(TestList(Path(self._dir.name) / "tested"), self.choice).mode, TESTING)
        with self.assertRaises(ValueError):
            self.view.set_mode("some")
        self.choice["test_view_mode"] = "gone"
        self.assertEqual(self.view.mode, NORMAL)


if __name__ == "__main__":
    unittest.main()
