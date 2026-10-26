from typing import Any

from streamer_toolbox.connections.twitch.boxes.twitch_clip_box import TwitchClipBox


class UpdateClipDownloader(TwitchClipBox):
    name = "update_clip_downloader"
    label = "Update clip downloader"
    help = "Asks GitHub now whether there is a newer TwitchDownloaderCLI and takes it (the toolbox does that by " \
           "itself once a day when Download clip is used). E.g. when clips stopped downloading after a change at " \
           "Twitch"
    group = "Stream"
    outputs = {"version": "text", "updated": "yes/no"}

    async def run(self) -> dict[str, Any]:
        return await self._downloader.update()
