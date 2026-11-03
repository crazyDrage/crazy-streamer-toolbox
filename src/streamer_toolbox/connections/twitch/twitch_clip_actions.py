from streamer_toolbox.connections.twitch.boxes.clip_video_address import ClipVideoAddress
from streamer_toolbox.connections.twitch.boxes.download_clip import DownloadClip
from streamer_toolbox.connections.twitch.boxes.update_clip_downloader import UpdateClipDownloader
from streamer_toolbox.connections.twitch.twitch_clip_downloader import TwitchClipDownloader
from streamer_toolbox.connections.twitch.twitch_clip_files import TwitchClipFiles
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class TwitchClipActions:
    """The boxes that make a clip playable in OBS. Clip video address: a clip's id or link → the address of its
    video file, played with no download (see TwitchClipFiles for where it comes from and why it is
    unofficial). Download clip: the clip as a file on this PC, made by TwitchDownloaderCLI, which the toolbox
    gets from GitHub and keeps up to date (TwitchClipDownloader); Update clip downloader asks for a newer one
    now. Play video once takes either. None needs a login: any public clip of any channel.

    One Box class per box, in boxes/."""

    def __init__(self, files: TwitchClipFiles, downloader: TwitchClipDownloader | None = None) -> None:
        self._files = files
        self._downloader = downloader

    def add_to(self, actions: ActionRegistry) -> None:
        boxes = [ClipVideoAddress(self._files, self._downloader)]
        if self._downloader is not None:  # without a downloader there's nothing to download with
            boxes += [DownloadClip(self._files, self._downloader), UpdateClipDownloader(self._files, self._downloader)]
        for box in boxes:
            actions.add_box(box, "twitch")
