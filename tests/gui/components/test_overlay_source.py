import unittest
from unittest import mock

from streamer_toolbox.connections.obs.obs_new_source_actions import ObsNewSourceActions
from streamer_toolbox.connections.obs.obs_request_actions import ObsRequestActions
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.connections.obs.obs_scene_actions import ObsSceneActions
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.gui.components.overlay_source import OverlaySource
from tests.fakes.fake_obs_script import FakeObsScript


class TestOverlaySource(unittest.IsolatedAsyncioTestCase):
    """His round 84: Add to OBS refused when the source was in another scene already (OBS code 601)."""

    def build(self, responses: dict) -> None:
        self.obs = FakeObsScript({"GetVideoSettings": {"baseWidth": 1920, "baseHeight": 1080},
                                  "CreateInput": {"sceneItemId": 4}, "CreateSceneItem": {"sceneItemId": 9},
                                  **responses})
        actions = ActionRegistry()
        requests = ObsRequests(self.obs.call)
        for part in (ObsRequestActions(self.obs.call), ObsNewSourceActions(requests), ObsSceneActions(requests)):
            part.add_to(actions)
        self.source = OverlaySource(actions)
        patcher = mock.patch("streamer_toolbox.gui.components.overlay_source.ui.notify")
        self.notify = patcher.start()
        self.addCleanup(patcher.stop)

    async def test_a_new_source_is_made(self) -> None:
        self.build({"GetInputSettings": None})  # OBS: not found
        self.assertTrue(await self.source.add("Gaming", "toolbox alerts", "http://x/overlay"))
        self.assertEqual(self.obs.sent("CreateInput")[0]["inputName"], "toolbox alerts")
        self.assertEqual(self.obs.sent("CreateSceneItem"), [])

    async def test_one_in_another_scene_goes_into_this_scene_too(self) -> None:
        self.build({"GetInputSettings": {"inputKind": "browser_source", "inputSettings": {}},
                    "GetSceneItemId": None})  # not in this scene yet
        self.assertTrue(await self.source.add("Gaming", "toolbox alerts", "http://x/overlay"))
        self.assertEqual(self.obs.sent("CreateInput"), [])
        self.assertEqual(self.obs.sent("CreateSceneItem"), [
            {"sceneName": "Gaming", "sourceName": "toolbox alerts", "sceneItemEnabled": True}])
        self.assertIn("the same source", self.notify.call_args.args[0])

    async def test_already_in_this_scene_or_another_kind(self) -> None:
        self.build({"GetInputSettings": {"inputKind": "browser_source"}, "GetSceneItemId": {"sceneItemId": 2}})
        self.assertTrue(await self.source.add("Gaming", "toolbox alerts", "http://x/overlay"))
        self.assertEqual(self.obs.sent("CreateSceneItem"), [])
        self.build({"GetInputSettings": {"inputKind": "image_source"}})
        self.assertFalse(await self.source.add("Gaming", "toolbox alerts", "http://x/overlay"))
        self.assertIn("isn't a Browser source", self.notify.call_args.args[0])
        self.assertEqual(self.obs.sent("CreateInput"), [])


if __name__ == "__main__":
    unittest.main()
