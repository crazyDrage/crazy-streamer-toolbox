import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.media.mp4_header_probe import Mp4HeaderProbe
from streamer_toolbox.core.media.orientation import Orientation
from streamer_toolbox.core.media.video_size import VideoSize
from tests.helpers.mp4_builder import Mp4Builder


class TestMp4HeaderProbe(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.probe = Mp4HeaderProbe()

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _write(self, data: bytes) -> Path:
        path = Path(self._dir.name, "video.mp4")
        path.write_bytes(data)
        return path

    def test_length_from_the_movie_header(self) -> None:
        path = self._write(Mp4Builder.movie(Mp4Builder.tkhd(1920, 1080), mvhd=Mp4Builder.mvhd(1000, 6500)))
        self.assertEqual(self.probe.length(path), 6.5)
        long = self._write(Mp4Builder.movie(Mp4Builder.tkhd(1920, 1080), mvhd=Mp4Builder.mvhd(90000, 2**33, 1),
                                            mdat_first=True))
        self.assertAlmostEqual(self.probe.length(long), 2**33 / 90000)
        self.assertIsNone(self.probe.length(self._write(Mp4Builder.movie(Mp4Builder.tkhd(1920, 1080)))))
        for duration in (0, 0xFFFFFFFF):  # fragmented / streamed files keep no length here
            self.assertIsNone(self.probe.length(self._write(
                Mp4Builder.movie(Mp4Builder.tkhd(1920, 1080), mvhd=Mp4Builder.mvhd(1000, duration)))))
        self.assertIsNone(self.probe.length(Path(self._dir.name, "missing.mp4")))

    def test_landscape_clip(self) -> None:
        path = self._write(Mp4Builder.movie(Mp4Builder.tkhd(1920, 1080)))
        size = self.probe.probe(path)
        self.assertEqual(size, VideoSize(1920, 1080))
        self.assertEqual(size.orientation, Orientation.LANDSCAPE)

    def test_portrait_clip(self) -> None:
        path = self._write(Mp4Builder.movie(Mp4Builder.tkhd(1080, 1920)))
        self.assertEqual(self.probe.probe(path).orientation, Orientation.PORTRAIT)

    def test_phone_video_with_rotation_flag_is_portrait(self) -> None:
        path = self._write(Mp4Builder.movie(Mp4Builder.tkhd(1920, 1080, Mp4Builder.ROTATE_90)))
        self.assertEqual(self.probe.probe(path), VideoSize(1080, 1920))

    def test_skips_audio_track(self) -> None:
        audio = Mp4Builder.tkhd(0, 0)
        video = Mp4Builder.tkhd(1280, 720)
        path = self._write(Mp4Builder.movie(audio, video))
        self.assertEqual(self.probe.probe(path), VideoSize(1280, 720))

    def test_moov_after_mdat(self) -> None:
        path = self._write(Mp4Builder.movie(Mp4Builder.tkhd(720, 1280), mdat_first=True))
        self.assertEqual(self.probe.probe(path), VideoSize(720, 1280))

    def test_version_1_tkhd(self) -> None:
        path = self._write(Mp4Builder.movie(Mp4Builder.tkhd(1080, 1080, version=1)))
        self.assertEqual(self.probe.probe(path).orientation, Orientation.SQUARE)

    def test_not_an_mp4_returns_none(self) -> None:
        path = self._write(b"this is not a video file at all")
        self.assertIsNone(self.probe.probe(path))

    def test_missing_file_returns_none(self) -> None:
        self.assertIsNone(self.probe.probe(Path(self._dir.name, "missing.mp4")))


if __name__ == "__main__":
    unittest.main()
