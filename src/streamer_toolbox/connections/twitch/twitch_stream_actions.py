from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.connections.twitch.boxes.announcement import Announcement
from streamer_toolbox.connections.twitch.boxes.cancel_raid import CancelRaid
from streamer_toolbox.connections.twitch.boxes.chat_mode import ChatMode
from streamer_toolbox.connections.twitch.boxes.create_clip import CreateClip
from streamer_toolbox.connections.twitch.boxes.end_poll import EndPoll
from streamer_toolbox.connections.twitch.boxes.end_prediction import EndPrediction
from streamer_toolbox.connections.twitch.boxes.get_chatters import GetChatters
from streamer_toolbox.connections.twitch.boxes.get_clips import GetClips
from streamer_toolbox.connections.twitch.boxes.run_ad_break import RunAdBreak
from streamer_toolbox.connections.twitch.boxes.shoutout import Shoutout
from streamer_toolbox.connections.twitch.boxes.start_poll import StartPoll
from streamer_toolbox.connections.twitch.boxes.start_prediction import StartPrediction
from streamer_toolbox.connections.twitch.boxes.start_raid import StartRaid
from streamer_toolbox.connections.twitch.boxes.timeout_ban import TimeoutBan
from streamer_toolbox.connections.twitch.boxes.twitch_stream_box import Helix
from streamer_toolbox.connections.twitch.boxes.untimeout_unban import UntimeoutUnban
from streamer_toolbox.core.actions.action_registry import ActionRegistry
import random
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any



class TwitchStreamActions:
    """Twitch boxes that need the permissions asked for on top of the login's basic ones (EXTRA_SCOPES in
    twitch_auth; he said yes to all of them on 2026-10-03): clip, shoutout, announcement, poll, prediction,
    raid, ad break, chat modes, timeout / ban, who is in chat. A login from before doesn't have them yet: such
    a box then says "press Connect once", the rest of the toolbox keeps working. Also "Get clips" (a channel's
    clips, one picked at random; Twitch asks no permission for that).

    One Box class per box, in boxes/."""

    def __init__(self, helix: Helix, me: Callable[[], OAuthToken],
                 pick: Callable[[list], Any] = random.choice,
                 now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> None:
        self._helix = helix
        self._me = me
        self._pick = pick
        self._now = now

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (CreateClip(self._helix, self._me, self._pick, self._now), GetClips(self._helix, self._me,
                    self._pick, self._now), RunAdBreak(self._helix, self._me, self._pick, self._now),
                    StartRaid(self._helix, self._me, self._pick, self._now), CancelRaid(self._helix, self._me,
                    self._pick, self._now), Shoutout(self._helix, self._me, self._pick, self._now),
                    Announcement(self._helix, self._me, self._pick, self._now), ChatMode(self._helix, self._me,
                    self._pick, self._now), GetChatters(self._helix, self._me, self._pick, self._now),
                    TimeoutBan(self._helix, self._me, self._pick, self._now), UntimeoutUnban(self._helix, self._me,
                    self._pick, self._now), StartPoll(self._helix, self._me, self._pick, self._now),
                    EndPoll(self._helix, self._me, self._pick, self._now), StartPrediction(self._helix, self._me,
                    self._pick, self._now), EndPrediction(self._helix, self._me, self._pick, self._now)):
            actions.add_box(box, "twitch")
