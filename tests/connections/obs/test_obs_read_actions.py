import unittest

from streamer_toolbox.connections.obs.obs_read_actions import ObsReadActions
from streamer_toolbox.connections.obs.obs_request_error import ObsRequestError
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from tests.fakes.fake_obs_script import FakeObsScript

NAMES = ("get_scenes", "get_sources", "get_studio_mode", "get_preview_scene", "get_profile", "get_scene_collection")


class TestObsReadActions(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.obs = FakeObsScript({
            "GetSceneList": {"scenes": [{"sceneName": "desktop"}, {"sceneName": "game"}]},
            "GetInputList": {"inputs": [{"inputName": "mic"}, {"inputName": "Camera"}]},
            "GetStudioModeEnabled": {"studioModeEnabled": True},
            "GetCurrentPreviewScene": {"currentPreviewSceneName": "game", "sceneUuid": "x"},
            "GetProfileList": {"currentProfileName": "testing", "profiles": ["testing", "live"]},
            "GetSceneCollectionList": {"currentSceneCollectionName": "testing", "sceneCollections": ["testing"]}})
        self.actions = ActionRegistry()
        ObsReadActions(ObsRequests(self.obs.call)).add_to(self.actions)

    async def test_each_box_reads_what_obs_has(self) -> None:
        self.assertEqual(await self.actions.run("obs.get_scenes"), ["game", "desktop"])
        self.assertEqual(await self.actions.run("obs.get_sources"), ["Camera", "mic"])
        self.assertIs(await self.actions.run("obs.get_studio_mode"), True)
        self.assertEqual(await self.actions.run("obs.get_preview_scene"), "game")
        self.assertEqual(await self.actions.run("obs.get_profile"), "testing")
        self.assertEqual(await self.actions.run("obs.get_scene_collection"), "testing")
        self.assertFalse([kind for kind in self.obs.kinds() if not kind.startswith("Get")])

    def test_all_are_live_values(self) -> None:
        for name in NAMES:
            with self.subTest(box=name):
                self.assertTrue(self.actions.get(f"obs.{name}").live)

    async def test_preview_scene_is_empty_while_studio_mode_is_off(self) -> None:
        self.obs.responses["GetCurrentPreviewScene"] = None  # the fake fails with 600 ...
        with self.assertRaises(ObsRequestError):
            await self.actions.run("obs.get_preview_scene")
        studio_off = ObsRequestError("GetCurrentPreviewScene", 506, None)

        async def failing(kind: str, data: dict | None = None) -> dict:
            raise studio_off

        actions = ActionRegistry()
        ObsReadActions(failing).add_to(actions)  # ... so 506 comes from a stand-in for ObsRequests
        self.assertEqual(await actions.run("obs.get_preview_scene"), "")


if __name__ == "__main__":
    unittest.main()
