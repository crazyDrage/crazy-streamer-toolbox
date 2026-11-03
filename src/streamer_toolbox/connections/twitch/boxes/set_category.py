from streamer_toolbox.connections.twitch.boxes.twitch_channel_box import TwitchChannelBox, _first


class SetCategory(TwitchChannelBox):
    name = "set_category"
    label = "Set category"
    help = "Changes your stream category (game) by its name, e.g. Just Chatting; gives the name Twitch found"
    hints = {"category": "the name as on Twitch; a close one is taken if it isn't exact"}
    group = "Stream"

    async def run(self, category: str) -> str:
        name = str(category).strip()
        if not name:
            raise ValueError("which category? (it is empty)")
        found = _first(await self._helix("GET", "games", params={"name": name})) or \
            _first(await self._helix("GET", "search/categories", params={"query": name, "first": 1}))
        if not found:
            raise LookupError(f"Twitch has no category like {name!r}")
        await self._helix("PATCH", "channels", params={"broadcaster_id": self._me().user_id},
                          json={"game_id": found["id"]})
        return found["name"]
