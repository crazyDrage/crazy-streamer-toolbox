from typing import Any

from streamer_toolbox.connections.twitch.twitch_clip_downloader import TwitchClipDownloader
from streamer_toolbox.connections.twitch.twitch_clip_files import TwitchClipFiles, clip_id
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.box_value import to_bool

BEST = "best"
QUALITIES = (BEST, "1080", "720", "480", "360")


class TwitchClipActions:
    """The boxes that make a clip playable in OBS. Clip video address: a clip's id or link → the address of its
    video file, played with no download (see TwitchClipFiles for where it comes from and why it is
    unofficial). Download clip: the clip as a file on this PC, made by TwitchDownloaderCLI, which the toolbox
    gets from GitHub and keeps up to date (TwitchClipDownloader); Update clip downloader asks for a newer one
    now. Play video once takes either. None needs a login: any public clip of any channel."""

    def __init__(self, files: TwitchClipFiles, downloader: TwitchClipDownloader | None = None) -> None:
        self._files = files
        self._downloader = downloader

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("twitch.clip_address", self.address, "Where a clip's video is, so Play video once can play it "
                    "straight from Twitch: no download, and no content warning page. Ask right before playing "
                    "(the address is good for some hours). Uses the way Twitch's own player asks, which Twitch "
                    "may change", "Clip video address", group="Stream",
                    options={"quality": _qualities},
                    labels={"finder": "Question finder"},
                    hints={"clip": "a clip's id (Get clips gives it) or its link",
                           "quality": "the best there is at or below this",
                           "finder": "only used when Twitch refuses the ways the toolbox knows: it then reads "
                                     "from Twitch's own clip player how to ask now (slower that one time: a "
                                     "few MB; kept for a week). Off: the box fails instead"},
                    outputs={"address": "text", "quality": "number", "id": "text"})
        if self._downloader is None:
            return
        actions.add("twitch.download_clip", self.download, "Downloads a clip as a video file for Play video once "
                    "(a few seconds). The same clip is not downloaded twice; the newest 20 files are kept. Uses "
                    "the program TwitchDownloaderCLI, which the toolbox gets from its GitHub page the first "
                    "time (about 50 MB) and keeps up to date", "Download clip", group="Stream",
                    options={"quality": _qualities},
                    hints={"clip": "a clip's id (Get clips gives it) or its link",
                           "quality": "if the clip doesn't have it, its best is taken"},
                    outputs={"file": "text", "id": "text"})
        actions.add("twitch.update_clip_downloader", self.update, "Asks GitHub now whether there is a newer "
                    "TwitchDownloaderCLI and takes it (the toolbox does that by itself once a day when Download "
                    "clip is used). E.g. when clips stopped downloading after a change at Twitch",
                    "Update clip downloader", group="Stream", outputs={"version": "text", "updated": "yes/no"})

    async def download(self, clip: str, quality: str = BEST) -> dict[str, Any]:
        file = await self._downloader.download(clip, quality)
        return {"file": str(file), "id": clip_id(clip)}

    async def update(self) -> dict[str, Any]:
        return await self._downloader.update()

    async def address(self, clip: str, quality: str = BEST, finder: bool = True) -> dict[str, Any]:
        files = await self._files.files(clip, to_bool(finder))
        wanted = str(quality).strip().casefold().removesuffix("p")
        if wanted not in ("", BEST):
            if not wanted.isdigit():
                raise ValueError(f"quality is {', '.join(QUALITIES)}, not {quality!r}")
            # the best at or below what was asked for; a clip that only has better ones gives its smallest
            files = [one for one in files if one["quality"] <= int(wanted)] or files[-1:]
        return {"address": files[0]["address"], "quality": files[0]["quality"], "id": clip_id(clip)}


async def _qualities() -> list[str]:
    return list(QUALITIES)
