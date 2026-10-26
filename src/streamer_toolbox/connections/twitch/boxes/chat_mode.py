from typing import Any

from streamer_toolbox.connections.twitch.boxes.twitch_stream_box import TwitchStreamBox, ON_OFF, _given, _on_off


class ChatMode(TwitchStreamBox):
    name = "chat_mode"
    label = "Chat mode"
    help = "Switches chat modes: emote only, slow mode, followers only, subscribers only. A field left empty " \
           "stays as it is"
    options = {"emote_only": _on_off, "subscribers_only": _on_off}
    hints = {"slow_seconds": "3 to 120, 0 = off, empty = leave",
             "followers_minutes": "how long they must follow: 0 = any follower, -1 = off, "

                                  "empty = leave"}
    group = "Chat"

    async def run(self, emote_only: str = "", slow_seconds: Any = "", followers_minutes: Any = "",
                  subscribers_only: str = "") -> None:
        self._allowed("moderator:manage:chat_settings")
        settings: dict[str, Any] = {}
        if emote_only in ON_OFF:
            settings["emote_mode"] = emote_only == "on"
        if subscribers_only in ON_OFF:
            settings["subscriber_mode"] = subscribers_only == "on"
        if _given(slow_seconds):
            wait = int(slow_seconds)
            settings["slow_mode"] = wait > 0
            if wait > 0:
                settings["slow_mode_wait_time"] = max(3, min(wait, 120))
        if _given(followers_minutes):
            minutes = int(followers_minutes)
            settings["follower_mode"] = minutes >= 0
            if minutes >= 0:
                settings["follower_mode_duration"] = min(minutes, 129600)
        if not settings:
            raise ValueError("nothing to change: every field is empty")
        await self._helix("PATCH", "chat/settings", params=self._as_moderator(), json=settings)
