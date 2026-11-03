from typing import TYPE_CHECKING, Any

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.twitch_connection import TwitchConnection


class GetRewards(Box):
    name = "rewards"
    label = "Get rewards"
    help = "Every channel point reward as a list: title, id, cost, enabled, paused, by_toolbox (only those can " \
           "be changed or refunded)"
    group = "Channel points"
    live = True

    def __init__(self, twitch: "TwitchConnection") -> None:
        self._twitch = twitch

    async def run(self) -> list[dict[str, Any]]:
        return await self._twitch.rewards()
