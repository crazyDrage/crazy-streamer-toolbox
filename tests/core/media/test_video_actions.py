import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.media.video_actions import VideoActions
from streamer_toolbox.core.media.video_size import VideoSize
from tests.fakes.fake_video_probe import FakeVideoProbe


class TestVideoActions(unittest.IsolatedAsyncioTestCase):
    async def test_info_gives_size_length_and_orientation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clip, unknown = Path(tmp, "clip.mp4"), Path(tmp, "other.webm")
            clip.write_bytes(b"x")
            unknown.write_bytes(b"x")
            video = VideoActions(FakeVideoProbe({"clip.mp4": VideoSize(720, 1280)}, {"clip.mp4": 12.3456}))
            self.assertEqual(await video.info(f'"{clip}"'),  # a path copied with quotes still works
                             {"width": 720, "height": 1280, "seconds": 12.346, "orientation": "portrait"})
            with self.assertRaisesRegex(ValueError, "only MP4"):
                await video.info(str(unknown))
            with self.assertRaisesRegex(FileNotFoundError, "no video file"):
                await video.info(str(Path(tmp, "gone.mp4")))
