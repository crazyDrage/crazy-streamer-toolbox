import unittest
from pathlib import Path

from streamer_toolbox.connections.obs.fit_media_by_orientation import FitMediaByOrientation
from streamer_toolbox.core.layout.box import Box
from streamer_toolbox.core.layout.orientation_layout_policy import OrientationLayoutPolicy
from streamer_toolbox.core.media.video_size import VideoSize
from tests.fakes.fake_scene_item_editor import FakeSceneItemEditor
from tests.fakes.fake_video_probe import FakeVideoProbe

LANDSCAPE_BOUNDS = Box(1300, 700, 576, 324)
PORTRAIT_BOUNDS = Box(1500, 100, 400, 900)
SCENES = ["desktop", "Just_chatting"]


class TestFitMediaByOrientation(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.editor = FakeSceneItemEditor()
        probe = FakeVideoProbe({"wide.mp4": VideoSize(1920, 1080), "tall.mp4": VideoSize(1080, 1920)})
        policy = OrientationLayoutPolicy(LANDSCAPE_BOUNDS, PORTRAIT_BOUNDS)
        self.action = FitMediaByOrientation(probe, policy, self.editor, "sound_alert", SCENES)

    async def test_portrait_video_moves_same_source_in_every_scene(self) -> None:
        bounds = await self.action.fit(Path("tall.mp4"))
        self.assertEqual(bounds, PORTRAIT_BOUNDS)
        self.assertEqual(self.editor.calls, [(scene, "sound_alert", PORTRAIT_BOUNDS) for scene in SCENES])

    async def test_landscape_video_gets_landscape_bounds(self) -> None:
        await self.action.fit(Path("wide.mp4"))
        self.assertEqual({call[2] for call in self.editor.calls}, {LANDSCAPE_BOUNDS})

    async def test_unknown_size_leaves_obs_untouched(self) -> None:
        self.assertIsNone(await self.action.fit(Path("unknown.mp4")))
        self.assertEqual(self.editor.calls, [])


if __name__ == "__main__":
    unittest.main()
