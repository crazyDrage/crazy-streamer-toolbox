import unittest

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.config.fit_target_config import FitTargetConfig
from streamer_toolbox.core.layout.box import Box
from streamer_toolbox.core.media.video_size import VideoSize
from streamer_toolbox.connections.obs.obs_fit_actions import add_fit_actions
from tests.fakes.fake_scene_item_editor import FakeSceneItemEditor
from tests.fakes.fake_video_probe import FakeVideoProbe

PORTRAIT = Box(1500, 100, 182, 324)
TARGET = FitTargetConfig("raid_clip", "raid_video_clip", ("desktop", "Just_chatting"),
                         Box(0, 0, 576, 324), PORTRAIT)


class TestObsFitActions(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.actions = ActionRegistry()
        self.editor = FakeSceneItemEditor()
        add_fit_actions(self.actions, (TARGET,), FakeVideoProbe({"tall.mp4": VideoSize(1080, 1920)}), self.editor)

    async def test_action_fits_source_in_every_scene(self) -> None:
        result = await self.actions.run("obs.fit_raid_clip", video_path="C:/clips/tall.mp4")
        self.assertEqual(result, {"fitted": True, "x": 1500, "y": 100, "width": 182, "height": 324})
        self.assertEqual(self.editor.calls, [("desktop", "raid_video_clip", PORTRAIT),
                                             ("Just_chatting", "raid_video_clip", PORTRAIT)])

    async def test_unknown_size_reports_and_leaves_obs_alone(self) -> None:
        result = await self.actions.run("obs.fit_raid_clip", video_path="missing.mp4")
        self.assertFalse(result["fitted"])
        self.assertEqual(self.editor.calls, [])


if __name__ == "__main__":
    unittest.main()
