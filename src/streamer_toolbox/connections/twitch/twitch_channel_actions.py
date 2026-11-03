from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.connections.twitch.boxes.channel_info import ChannelInfo
from streamer_toolbox.connections.twitch.boxes.followers import Followers
from streamer_toolbox.connections.twitch.boxes.get_twitch_user import GetTwitchUser
from streamer_toolbox.connections.twitch.boxes.next_ad_break import NextAdBreak
from streamer_toolbox.connections.twitch.boxes.set_category import SetCategory
from streamer_toolbox.connections.twitch.boxes.set_stream_title import SetStreamTitle
from streamer_toolbox.connections.twitch.boxes.twitch_channel_box import Helix
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from collections.abc import Callable
from datetime import datetime, timezone



class TwitchChannelActions:
    """Twitch boxes for the channel and its viewers that the login allows already (no new permissions): is the
    stream live (viewers, uptime), title and category (read and change), a viewer's profile, followers, the
    next ad break.

    One Box class per box, in boxes/."""

    def __init__(self, helix: Helix, me: Callable[[], OAuthToken],
                 now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> None:
        self._helix = helix
        self._me = me
        self._now = now

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (ChannelInfo(self._helix, self._me, self._now), SetStreamTitle(self._helix, self._me, self._now),
                    SetCategory(self._helix, self._me, self._now), NextAdBreak(self._helix, self._me, self._now),
                    GetTwitchUser(self._helix, self._me, self._now), Followers(self._helix, self._me, self._now)):
            actions.add_box(box, "twitch")
