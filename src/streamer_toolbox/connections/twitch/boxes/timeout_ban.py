from typing import Any

from streamer_toolbox.connections.twitch.boxes.twitch_stream_box import TwitchStreamBox


class TimeoutBan(TwitchStreamBox):
    name = "timeout"
    label = "Timeout / ban"
    help = "Times a viewer out; seconds 0 = a ban until you unban"
    hints = {"seconds": "1 to 1209600 (two weeks); 0 = ban"}
    group = "Viewers"

    async def run(self, user: str, seconds: int = 600, reason: str = "") -> None:
        self._allowed("moderator:manage:banned_users")
        ban: dict[str, Any] = {"user_id": (await self._user(user))["id"], "reason": str(reason)[:500]}
        if int(seconds) > 0:
            ban["duration"] = min(int(seconds), 1209600)
        await self._helix("POST", "moderation/bans", params=self._as_moderator(), json={"data": ban})
