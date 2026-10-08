import unittest

from streamer_toolbox.connections.obs.obs_placement import ObsPlacement
from streamer_toolbox.connections.obs.obs_placement_actions import MARKER_COLOR, ObsPlacementActions
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from tests.fakes.fake_obs_script import FakeObsScript

DRAGGED = {"positionX": 1600.4, "positionY": 50.0, "rotation": 0.0, "alignment": 5, "boundsType": "OBS_BOUNDS_NONE",
           "boundsWidth": 0.0, "boundsHeight": 0.0, "width": 320.0, "height": 180.0, "scaleX": 0.5}
PLACE = {"x": 1600.4, "y": 50.0, "width": 320.0, "height": 180.0, "rotation": 0.0, "alignment": 5,
         "scene": "toolbox_test"}


class TestObsPlacementActions(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.obs = FakeObsScript({"CreateInput": {"sceneItemId": 21}, "GetSceneItemId": {"sceneItemId": 21},
                                  "GetSceneItemTransform": {"sceneItemTransform": DRAGGED}})
        self.actions = ActionRegistry()
        ObsPlacementActions(ObsRequests(self.obs.call)).add_to(self.actions)

    async def test_a_marker_goes_out_is_read_and_removed(self) -> None:
        made = await self.actions.run("obs.put_place_marker", scene="toolbox_test")
        created = self.obs.sent("CreateInput")[0]
        self.assertEqual((created["inputKind"], created["inputSettings"]),
                         ("color_source_v3", {"color": MARKER_COLOR, "width": 640, "height": 360}))
        self.assertTrue(made["source"].startswith("toolbox place marker "))
        self.assertEqual(self.obs.sent("SetSceneItemTransform"), [])  # no place yet: top left
        place = await self.actions.run("obs.take_place_marker", scene="toolbox_test", source=made["source"])
        self.assertEqual(place, PLACE)
        self.assertEqual(self.obs.kinds()[-1], "RemoveInput")
        self.assertEqual(self.obs.sent("RemoveInput"), [{"inputName": made["source"]}])

    async def test_a_marker_starts_at_the_place_the_box_has(self) -> None:
        await self.actions.run("obs.put_place_marker", scene="toolbox_test", place=PLACE)
        self.assertEqual(self.obs.sent("CreateInput")[0]["inputSettings"]["width"], 320)
        self.assertEqual(self.obs.sent("SetSceneItemTransform")[0]["sceneItemTransform"],
                         {"positionX": 1600.4, "positionY": 50.0, "rotation": 0.0, "alignment": 5})

    async def test_cancel_only_removes_the_marker(self) -> None:
        gone = await self.actions.run("obs.take_place_marker", scene="s", source="toolbox place marker ab12cd",
                                      keep="false")
        self.assertEqual((gone, self.obs.kinds()), ({}, ["RemoveInput"]))

    async def test_a_marker_that_cant_be_read_is_still_removed(self) -> None:
        self.obs.responses["GetSceneItemTransform"] = None
        with self.assertRaisesRegex(Exception, "GetSceneItemTransform failed"):
            await self.actions.run("obs.take_place_marker", scene="s", source="m")
        self.assertEqual(self.obs.kinds()[-1], "RemoveInput")

    async def test_place_source_fits_it_into_the_box(self) -> None:
        await self.actions.run("obs.place_source", scene="toolbox_test", source="clip", place=PLACE)
        self.assertEqual(self.obs.sent("SetSceneItemTransform"), [{
            "sceneName": "toolbox_test", "sceneItemId": 21, "sceneItemTransform": {
                "positionX": 1600.4, "positionY": 50.0, "rotation": 0.0, "alignment": 5,
                "boundsType": "OBS_BOUNDS_SCALE_INNER", "boundsAlignment": 0, "boundsWidth": 320.0,
                "boundsHeight": 180.0}}])
        with self.assertRaisesRegex(ValueError, "Set up the place first"):
            await self.actions.run("obs.place_source", scene="s", source="clip", place="")
        with self.assertRaisesRegex(ValueError, "a place is an object"):
            await self.actions.run("obs.place_source", scene="s", source="clip", place="left")

    async def test_get_source_place_reads_bounds_when_it_has_them(self) -> None:
        self.obs.responses["GetSceneItemTransform"] = {"sceneItemTransform": DRAGGED | {
            "boundsType": "OBS_BOUNDS_SCALE_INNER", "boundsWidth": 400.0, "boundsHeight": 300.0}}
        place = await self.actions.run("obs.get_source_place", scene="desktop", source="sound_alert")
        self.assertEqual((place["width"], place["height"], place["scene"]), (400.0, 300.0, "desktop"))

    def test_a_place_in_words_and_without_a_size(self) -> None:
        self.assertEqual(ObsPlacement.from_value(PLACE).text(), "x 1600.4, y 50 · 320 × 180 · set up in toolbox_test")
        sound = ObsPlacement.from_value('{"x": 10, "y": 20}')  # JSON text works too
        self.assertEqual(sound.to_transform(), {"positionX": 10.0, "positionY": 20.0, "rotation": 0.0, "alignment": 5})


if __name__ == "__main__":
    unittest.main()
