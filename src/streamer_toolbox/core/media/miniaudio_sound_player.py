import array
import asyncio
from pathlib import Path

import miniaudio

from streamer_toolbox.core.interfaces.sound_player import SoundPlayer

RATE, CHANNELS = 48000, 2


class MiniaudioSoundPlayer(SoundPlayer):
    """SoundPlayer with miniaudio: decodes the whole file (ogg, mp3, wav, flac; alert sounds are short), scales
    it to the volume, and gives each sound its own playback device so sounds can overlap."""

    def __init__(self) -> None:
        self._playing: set[miniaudio.PlaybackDevice] = set()

    async def play(self, path: Path, volume: float = 1.0, wait: bool = False) -> float:
        samples = await asyncio.to_thread(decode, path, volume)
        seconds = len(samples) / CHANNELS / RATE
        device = miniaudio.PlaybackDevice(nchannels=CHANNELS, sample_rate=RATE, app_name="streamer-toolbox")
        stream = _chunks(samples)
        next(stream)
        device.start(stream)
        self._playing.add(device)
        task = asyncio.get_running_loop().create_task(self._close_after(device, seconds + 0.3))
        if wait:
            await task
        return seconds

    async def stop_all(self) -> int:
        devices, self._playing = list(self._playing), set()
        for device in devices:
            device.close()
        return len(devices)

    async def _close_after(self, device: miniaudio.PlaybackDevice, seconds: float) -> None:
        await asyncio.sleep(seconds)
        if device in self._playing:
            self._playing.discard(device)
            device.close()


def decode(path: Path, volume: float = 1.0) -> array.array:
    """The file as 16-bit stereo samples at 48 kHz, scaled to volume (0..1)."""
    if not Path(path).is_file():
        raise FileNotFoundError(f"no sound file {path}")
    samples = miniaudio.decode_file(str(path), nchannels=CHANNELS, sample_rate=RATE).samples
    volume = min(max(float(volume), 0.0), 1.0)
    if volume != 1.0:
        samples = array.array("h", (int(s * volume) for s in samples))
    return samples


def _chunks(samples: array.array):
    """miniaudio's generator protocol: it sends how many frames it wants, we yield them (then silence)."""
    position = 0
    frames = yield b""
    while True:
        end = position + frames * CHANNELS
        chunk = samples[position:end]
        position = end
        frames = yield chunk if len(chunk) else array.array("h", bytes(frames * CHANNELS * 2))
