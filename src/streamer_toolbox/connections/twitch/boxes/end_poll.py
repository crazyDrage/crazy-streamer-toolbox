from typing import Any

from streamer_toolbox.connections.twitch.boxes.twitch_stream_box import TwitchStreamBox, _first


class EndPoll(TwitchStreamBox):
    name = "end_poll"
    label = "End poll"
    help = "Ends the running poll and gives the result: the winner and every choice with its votes"
    outputs = {"winner": "text", "votes": "number", "choices": "list"}
    group = "Polls and predictions"

    async def run(self) -> dict[str, Any]:
        self._allowed("channel:manage:polls")
        me = self._me().user_id
        poll = _first(await self._helix("GET", "polls", params={"broadcaster_id": me, "first": 1}))
        if poll.get("status") != "ACTIVE":
            raise RuntimeError("no poll is running")
        ended = _first(await self._helix("PATCH", "polls", json={"broadcaster_id": me, "id": poll["id"],
                                                                "status": "TERMINATED"})) or poll
        choices = [{"title": c.get("title", ""), "votes": c.get("votes", 0)} for c in ended.get("choices") or []]
        best = max(choices, key=lambda c: c["votes"], default={"title": "", "votes": 0})
        return {"winner": best["title"], "votes": best["votes"], "choices": choices}
