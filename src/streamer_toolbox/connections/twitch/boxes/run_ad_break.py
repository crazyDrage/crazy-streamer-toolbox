from typing import Any

from streamer_toolbox.connections.twitch.boxes.twitch_stream_box import TwitchStreamBox, AD_LENGTHS, _ad_lengths, _first


class RunAdBreak(TwitchStreamBox):
    name = "run_ad"
    label = "Run ad break"
    help = "Starts an ad break now (only while live); gives its length and how long until the next one is possible"
    options = {"seconds": _ad_lengths}
    outputs = {"seconds": "number", "retry_after": "number"}
    group = "Stream"

    async def run(self, seconds: int = 60) -> dict[str, Any]:
        self._allowed("channel:edit:commercial")
        if int(seconds) not in AD_LENGTHS:
            raise ValueError(f"an ad break is {', '.join(map(str, AD_LENGTHS))} seconds long, not {seconds}")
        ad = _first(await self._helix("POST", "channels/commercial",
                                      json={"broadcaster_id": self._me().user_id, "length": int(seconds)}))
        return {"seconds": ad.get("length", int(seconds)), "retry_after": ad.get("retry_after", 0)}
