import unittest

from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.connections.obs.obs_scene_actions import ObsSceneActions
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from tests.fakes.fake_obs_script import FakeObsScript


class TestObsSceneActions(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.obs = FakeObsScript({
            "GetSceneTransitionList": {"transitions": [{"transitionName": "Fade"}, {"transitionName": "Cut"}]},
            "GetCurrentSceneTransition": {"transitionName": "Fade", "transitionDuration": 300},
            "GetSceneItemList": {"sceneItems": [
                {"sourceName": "background", "sceneItemIndex": 0, "sceneItemEnabled": True,
                 "inputKind": "image_source", "isGroup": None},
                {"sourceName": "desktop", "sceneItemIndex": 1, "sceneItemEnabled": False, "inputKind": None,
                 "isGroup": False},
                {"sourceName": "alerts", "sceneItemIndex": 2, "sceneItemEnabled": True, "inputKind": None,
                 "isGroup": True}]}})
        self.actions = ActionRegistry()
        ObsSceneActions(ObsRequests(self.obs.call)).add_to(self.actions)

    async def test_transition(self) -> None:
        self.assertEqual(await self.actions.get("obs.set_transition").options["transition"](), ["Fade", "Cut"])
        await self.actions.run("obs.set_transition", transition="Fade", seconds="0.5")
        await self.actions.run("obs.set_transition", transition="Cut")
        self.assertEqual([k for k in self.obs.kinds() if k.startswith("Set")], [
            "SetCurrentSceneTransition", "SetCurrentSceneTransitionDuration",
            "SetCurrentSceneTransition"])
        self.assertEqual(self.obs.sent("SetCurrentSceneTransitionDuration"), [{"transitionDuration": 500}])
        with self.assertRaisesRegex(ValueError, "0.05 to 20 seconds"):
            await self.actions.run("obs.set_transition", transition="Fade", seconds=30)
        self.assertEqual(await self.actions.run("obs.get_transition"), {"transition": "Fade", "seconds": 0.3})

    async def test_scene_sources_top_first(self) -> None:
        self.assertEqual(await self.actions.run("obs.get_scene_sources", scene="toolbox_test"), [
            {"source": "alerts", "visible": True, "kind": "group"},
            {"source": "desktop", "visible": False, "kind": "scene"},
            {"source": "background", "visible": True, "kind": "image_source"}])


if __name__ == "__main__":
    unittest.main()
