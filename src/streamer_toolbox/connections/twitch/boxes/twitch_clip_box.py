from streamer_toolbox.connections.twitch.twitch_clip_downloader import TwitchClipDownloader
from streamer_toolbox.connections.twitch.twitch_clip_files import TwitchClipFiles
from streamer_toolbox.core.actions.fixed_choices import fixed_choices
from streamer_toolbox.core.interfaces.box import Box

BEST = "best"
QUALITIES = (BEST, "1080", "720", "480", "360")
QUALITY_PICKER = fixed_choices(QUALITIES)


class TwitchClipBox(Box):
    """What the clip boxes share (not a box itself: it has no run): where a clip's video is found
    (TwitchClipFiles) and the program that downloads one (TwitchClipDownloader; None = no download boxes)."""

    def __init__(self, files: TwitchClipFiles, downloader: TwitchClipDownloader | None = None) -> None:
        self._files = files
        self._downloader = downloader
