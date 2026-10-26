from typing import Any

from streamer_toolbox.connections.twitch.boxes.twitch_clip_box import BEST, QUALITY_PICKER, TwitchClipBox
from streamer_toolbox.connections.twitch.twitch_clip_files import clip_id


class DownloadClip(TwitchClipBox):
    name = "download_clip"
    label = "Download clip"
    help = "Downloads a clip as a video file for Play video once (a few seconds). The same clip is not downloaded " \
           "twice; the newest 20 files are kept. Uses the program TwitchDownloaderCLI, which the toolbox gets from " \
           "its GitHub page the first time (about 50 MB) and keeps up to date"
    group = "Stream"
    options = {"quality": QUALITY_PICKER}
    hints = {"clip": "a clip's id (Get clips gives it) or its link",
             "quality": "if the clip doesn't have it, its best is taken"}
    outputs = {"file": "text", "id": "text"}

    async def run(self, clip: str, quality: str = BEST) -> dict[str, Any]:
        file = await self._downloader.download(clip, quality)
        return {"file": str(file), "id": clip_id(clip)}
