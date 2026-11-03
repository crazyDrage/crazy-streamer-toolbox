from typing import Any

from streamer_toolbox.connections.twitch.boxes.twitch_stream_box import TwitchStreamBox, _first, _title, _titles


class StartPoll(TwitchStreamBox):
    name = "start_poll"
    label = "Start poll"
    help = "Starts a poll; gives its id"
    hints = {"choices": "2 to 5, separated by commas (or a list)", "seconds": "15 to 1800"}
    group = "Polls and predictions"

    async def run(self, title: str, choices: Any, seconds: int = 60) -> str:
        self._allowed("channel:manage:polls")
        titles = _titles(choices, 2, 5, "choices")
        poll = _first(await self._helix("POST", "polls", json={
            "broadcaster_id": self._me().user_id, "title": _title(title, 60),
            "choices": [{"title": t[:25]} for t in titles], "duration": max(15, min(int(seconds), 1800))}))
        return poll.get("id", "")
