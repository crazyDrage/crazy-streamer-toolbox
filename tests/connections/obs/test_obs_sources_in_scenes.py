import unittest

from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.connections.obs.obs_scene_actions import ObsSceneActions
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from tests.fakes.fake_obs_script import FakeObsScript


class TestObsSourcesInScenes(unittest.IsolatedAsyncioTestCase):
    """His round 82: the (scene, source) pairs, and showing / hiding all of them with that list."""

    def setUp(self) -> None:
        self.obs = FakeObsScript({
            "GetSceneList": {"scenes": [{"sceneName": "Gaming"}, {"sceneName": "Just_chatting"}]},
            "GetSceneItemList": [
                {"sceneItems": [{"sourceName": "so-event", "sceneItemId": 3, "sceneItemEnabled": False,
                                 "sceneItemIndex": 0},
                                {"sourceName": "cam", "sceneItemId": 1, "sceneItemEnabled": True,
                                 "sceneItemIndex": 1}]},
                {"sceneItems": [{"sourceName": "Overlays", "sceneItemId": 8, "isGroup": True,
                                 "sceneItemEnabled": True}]}],
            "GetGroupSceneItemList": {"sceneItems": [{"sourceName": "so-event", "sceneItemId": 2,
                                                      "sceneItemEnabled": True}]},
            "GetSceneItemId": {"sceneItemId": 5}})
        self.actions = ActionRegistry()
        ObsSceneActions(ObsRequests(self.obs.call)).add_to(self.actions)

    async def test_where_a_source_is_also_in_a_group(self) -> None:
        pairs = await self.actions.run("obs.sources_in_scenes", source="so-event")
        self.assertEqual(pairs, [{"scene": "Just_chatting", "source": "so-event", "visible": False, "item_id": 3},
                                 {"scene": "Overlays", "source": "so-event", "visible": True, "item_id": 2}])

    async def test_every_source_when_none_is_named(self) -> None:
        pairs = await self.actions.run("obs.sources_in_scenes")
        self.assertEqual([(p["scene"], p["source"]) for p in pairs],
                         [("Just_chatting", "cam"), ("Just_chatting", "so-event"), ("Gaming", "Overlays"),
                          ("Overlays", "so-event")])

    async def test_show_hide_the_whole_list(self) -> None:
        changed = await self.actions.run("obs.set_sources_visible", places=[
            {"scene": "Just_chatting", "source": "so-event", "item_id": 3},
            {"scene": "Gaming", "source": "so-event"}], visible="false")
        self.assertEqual(changed, 2)
        self.assertEqual(self.obs.sent("SetSceneItemEnabled"), [
            {"sceneName": "Just_chatting", "sceneItemId": 3, "sceneItemEnabled": False},
            {"sceneName": "Gaming", "sceneItemId": 5, "sceneItemEnabled": False}])
        self.assertEqual(self.obs.sent("GetSceneItemId"), [{"sceneName": "Gaming", "sourceName": "so-event"}])
        with self.assertRaisesRegex(ValueError, "needs a scene and a source"):
            await self.actions.run("obs.set_sources_visible", places=["so-event"])
        self.assertEqual(await self.actions.run("obs.set_sources_visible", places=[]), 0)


if __name__ == "__main__":
    unittest.main()
