import struct
import tempfile
import unittest
import wave
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.media.miniaudio_sound_player import decode
from streamer_toolbox.core.media.sound_actions import SoundActions
from tests.fakes.fake_sound_player import FakeSoundPlayer


def write_wav(path: Path, seconds: float = 0.5, level: int = 10000) -> None:
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(48000)
        out.writeframes(struct.pack("<h", level) * int(48000 * seconds))


class TestSoundActions(unittest.IsolatedAsyncioTestCase):
    async def test_play_finds_files_in_the_sound_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "alarms").mkdir()
            (folder / "alarms" / "short.ogg").write_bytes(b"")
            (folder / "bubbles.wav").write_bytes(b"")
            (folder / "notes.txt").write_text("x")
            player = FakeSoundPlayer()
            actions = ActionRegistry()
            SoundActions(player, folder).add_to(actions)
            self.assertEqual(await actions.run("sound.play", file="bubbles.wav", volume="0.4"), 1.5)
            self.assertEqual(await actions.get("sound.play").options["file"](),
                             [str(Path("alarms/short.ogg")), "bubbles.wav"])
        self.assertEqual(player.played, [(folder / "bubbles.wav", 0.4, False)])

    def test_decode_scales_the_volume(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tone.wav"
            write_wav(path)
            full = decode(path)
            quiet = decode(path, 0.5)
            with self.assertRaises(FileNotFoundError):
                decode(Path(tmp) / "missing.ogg")
        self.assertAlmostEqual(len(full) / 2 / 48000, 0.5, places=2)  # stereo at 48 kHz
        self.assertAlmostEqual(quiet[1000], full[1000] // 2, delta=1)


if __name__ == "__main__":
    unittest.main()
