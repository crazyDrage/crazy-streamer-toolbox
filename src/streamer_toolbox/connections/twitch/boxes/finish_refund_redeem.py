from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.twitch_connection import TwitchConnection


class FinishRefundRedeem(Box):
    name = "finish_redeem"
    label = "Finish / refund redeem"
    help = "Marks a redeem done, or refund = give the points back (e.g. when something failed). Wire reward_id " \
           "and redemption_id from the Start box. Only for rewards the toolbox made"
    group = "Channel points"

    def __init__(self, twitch: "TwitchConnection") -> None:
        self._twitch = twitch

    async def run(self, reward_id: str, redemption_id: str, refund: bool = False) -> None:
        return await self._twitch.finish_redeem(reward_id, redemption_id, refund)
