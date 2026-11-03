import unittest

from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.connections.obs.obs_scene_actions import ObsSceneActions
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from tests.fakes.fake_obs_script import FakeObsScript


class TestObsAddSourceToScenes(unittest.IsolatedAsyncioTestCase):
    """His round 83: the same source into every scene a template is in, and out again at the end."""

    def setUp(self) -> None:
        self.obs = FakeObsScript({
            "CreateSceneItem": [{"sceneItemId": 11}, {"sceneItemId": 12}],
            "GetSceneItemId": {"sceneItemId": 5},
            "GetSceneItemTransform": {"sceneItemTransform": {"positionX": 100.0, "positionY": 50.0, "scaleX": 0.5,
                                                             "scaleY": 0.5, "width": 960.0,
                                                             "boundsType": "OBS_BOUNDS_NONE", "boundsWidth": 0.0}},
            "GetSceneItemIndex": {"sceneItemIndex": 2}})
        self.actions = ActionRegistry()
        ObsSceneActions(ObsRequests(self.obs.call)).add_to(self.actions)

    async def test_into_every_scene_of_the_template_right_above_it(self) -> None:
        added = await self.actions.run("obs.add_source_to_scenes", source="clip-player", places=[
            {"scene": "Gaming", "source": "so-event", "visible": False, "item_id": 3},
            {"scene": "Just_chatting", "source": "so-event"}])
        self.assertEqual(added, [{"scene": "Gaming", "source": "clip-player", "item_id": 11},
                                 {"scene": "Just_chatting", "source": "clip-player", "item_id": 12}])
        self.assertEqual(self.obs.sent("CreateSceneItem"), [
            {"sceneName": "Gaming", "sourceName": "clip-player", "sceneItemEnabled": True},
            {"sceneName": "Just_chatting", "sourceName": "clip-player", "sceneItemEnabled": True}])
        self.assertEqual(self.obs.sent("GetSceneItemId"), [{"sceneName": "Just_chatting", "sourceName": "so-event"}])
        self.assertEqual(self.obs.sent("SetSceneItemTransform")[0], {
            "sceneName": "Gaming", "sceneItemId": 11,
            "sceneItemTransform": {"positionX": 100.0, "positionY": 50.0, "scaleX": 0.5, "scaleY": 0.5}})
        self.assertEqual(self.obs.sent("SetSceneItemIndex"), [
            {"sceneName": "Gaming", "sceneItemId": 11, "sceneItemIndex": 3},
            {"sceneName": "Just_chatting", "sceneItemId": 12, "sceneItemIndex": 3}])

    async def test_a_scene_name_and_without_placing(self) -> None:
        added = await self.actions.run("obs.add_source_to_scenes", source="clip-player", places="Gaming",
                                       visible="false")
        self.assertEqual(added, [{"scene": "Gaming", "source": "clip-player", "item_id": 11}])
        self.assertEqual(self.obs.sent("CreateSceneItem")[0]["sceneItemEnabled"], False)
        self.assertEqual(self.obs.sent("SetSceneItemTransform"), [])
        await self.actions.run("obs.add_source_to_scenes", source="clip-player", like="false",
                               places=[{"scene": "Gaming", "source": "so-event"}])
        self.assertEqual(self.obs.sent("SetSceneItemTransform"), [])
        with self.assertRaisesRegex(ValueError, "needs a scene"):
            await self.actions.run("obs.add_source_to_scenes", source="clip-player", places=[{"source": "x"}])
        with self.assertRaisesRegex(ValueError, "which source"):
            await self.actions.run("obs.add_source_to_scenes", source="", places="Gaming")

    async def test_take_out_keeps_the_source(self) -> None:
        taken = await self.actions.run("obs.take_out_of_scenes", places=[
            {"scene": "Gaming", "source": "clip-player", "item_id": 11},
            {"scene": "Just_chatting", "source": "clip-player"}])
        self.assertEqual(taken, 2)
        self.assertEqual(self.obs.sent("RemoveSceneItem"), [{"sceneName": "Gaming", "sceneItemId": 11},
                                                           {"sceneName": "Just_chatting", "sceneItemId": 5}])
        self.assertNotIn("RemoveInput", self.obs.kinds())
        with self.assertRaisesRegex(ValueError, "needs a scene and a source"):
            await self.actions.run("obs.take_out_of_scenes", places=["Gaming"])


if __name__ == "__main__":
    unittest.main()
