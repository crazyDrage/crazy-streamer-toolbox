from typing import Any

from streamer_toolbox.connections.twitch.boxes.twitch_channel_box import TwitchChannelBox, _first, _time


class NextAdBreak(TwitchChannelBox):
    name = "get_ad_schedule"
    label = "Next ad break"
    help = "When the next ad break comes (seconds from now), how long it is, snoozes left"
    live = True
    outputs = {"next_in_seconds": "number", "length_seconds": "number", "snoozes": "number"}
    group = "Stream"

    async def run(self) -> dict[str, Any]:
        ads = _first(await self._helix("GET", "channels/ads", params={"broadcaster_id": self._me().user_id}))
        next_at = _time(ads.get("next_ad_at"))
        return {"next_in_seconds": max(round((next_at - self._now()).total_seconds()), 0) if next_at else 0,
                "length_seconds": ads.get("duration", 0), "snoozes": ads.get("snooze_count", 0)}
