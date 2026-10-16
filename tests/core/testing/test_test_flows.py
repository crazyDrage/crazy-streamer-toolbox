import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.testing.test_flows import TestFlows
from streamer_toolbox.core.testing.test_item import BOX, PAGE, TRIGGER, TestItem
from streamer_toolbox.core.testing.test_list import TestList

MUTE = TestItem(BOX, "obs.mute", "Mute", "OBS", "Audio", "flows/boxes/obs/audio", "Flows > Boxes > OBS > Audio")
ITEMS = [TestItem(PAGE, "/variables", "Variables", "Variables", file="variables/page", heading="Variables"),
         MUTE,
         TestItem(BOX, "obs.get_scene", "Get scene", "OBS", "Scenes", "flows/boxes/obs/scenes",
                  "Flows > Boxes > OBS > Scenes"),
         TestItem(BOX, "obs.set_scene", "Set scene", "OBS", "Scenes", "flows/boxes/obs/scenes",
                  "Flows > Boxes > OBS > Scenes")]


class TestTestFlows(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.record = TestList(Path(self._dir.name) / "tested")
        self.record.sync(ITEMS)
        self.store = FlowStore(Path(self._dir.name) / "settings" / "flows")
        self.written = Path(self._dir.name) / "settings" / "test_flows.json"

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_every_box_gets_a_numbered_flow_with_start_and_itself(self) -> None:
        self.assertEqual(TestFlows(self.record, self.store, self.written).write(), (3, 0, 0))
        flows = self.store.all()
        self.assertEqual([(f.name, f.label, f.folder) for f in flows], [
            ("t001_obs_mute", "001 Mute", "01 OBS > Audio"),
            ("t002_obs_get_scene", "002 Get scene", "02 OBS > Scenes"),
            ("t003_obs_set_scene", "003 Set scene", "02 OBS > Scenes")])
        self.assertEqual([(n.id, n.action, n.params) for n in flows[0].nodes], [("n1", "obs.mute", {})])
        self.assertEqual(flows[0].targets("start", "out"), ["n1"])
        self.assertEqual(self.record.numbers(), {"box:obs.mute": 1, "box:obs.get_scene": 2, "box:obs.set_scene": 3})

    def test_writing_again_keeps_what_he_set_and_moves_the_numbers(self) -> None:
        TestFlows(self.record, self.store, self.written).write()
        mine = self.store.all()[1]
        self.store.save(replace(mine, nodes=(replace(mine.nodes[0], params={"scene": "desktop"}, box=(300, 120)),)))
        before = self.store.path_of("t001_obs_mute").stat().st_mtime_ns
        self.assertEqual(TestFlows(self.record, self.store, self.written).write(), (0, 3, 0))
        self.assertEqual(self.store.path_of("t001_obs_mute").stat().st_mtime_ns, before)  # nothing to change

        new = TestItem(BOX, "obs.fade", "Fade", "OBS", "Audio", "flows/boxes/obs/audio", "Flows > Boxes > OBS > Audio")
        self.record.sync([ITEMS[0], new, *ITEMS[1:]])
        self.assertEqual(TestFlows(self.record, self.store, self.written).write(), (1, 3, 0))
        flows = {f.name: f for f in self.store.all()}
        self.assertEqual(sorted(flows), ["t001_obs_fade", "t002_obs_mute", "t003_obs_get_scene",
                                         "t004_obs_set_scene"])
        moved = flows["t003_obs_get_scene"]
        self.assertEqual((moved.label, moved.nodes[0].params, moved.nodes[0].box),
                         ("003 Get scene", {"scene": "desktop"}, (300, 120)))

    def test_a_box_that_is_gone_keeps_its_flow_and_its_number_is_free(self) -> None:
        TestFlows(self.record, self.store, self.written).write()
        self.record.sync([item for item in ITEMS if item is not MUTE])
        TestFlows(self.record, self.store, self.written).write()
        self.assertEqual(sorted(f.name for f in self.store.all()),
                         ["t001_obs_get_scene", "t001_obs_mute", "t002_obs_set_scene"])

    def test_a_trigger_gets_no_flow(self) -> None:
        follow = TestItem(TRIGGER, "twitch.follow", "Follow", "Twitch", file="flows/triggers/twitch",
                          heading="Flows > Triggers > Twitch")
        self.record.sync([*ITEMS, follow])
        self.assertEqual(TestFlows(self.record, self.store, self.written).write(), (3, 0, 0))
        self.assertFalse(any(f.triggers for f in self.store.all()))

    def test_a_flow_he_deleted_stays_deleted_until_the_list_is_gone(self) -> None:
        TestFlows(self.record, self.store, self.written).write()
        self.store.delete("t001_obs_mute")
        self.assertEqual(TestFlows(self.record, self.store, self.written).write(), (0, 2, 1))
        self.assertNotIn("t001_obs_mute", [f.name for f in self.store.all()])
        self.written.unlink()
        self.assertEqual(TestFlows(self.record, self.store, self.written).write(), (1, 2, 0))
