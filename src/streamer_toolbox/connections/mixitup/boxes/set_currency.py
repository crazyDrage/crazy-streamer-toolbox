from streamer_toolbox.connections.mixitup.boxes.mixitup_box import MixitupBox, Send, _viewer_platforms


class SetCurrency(MixitupBox):
    name = "set_currency"
    label = "Set currency"
    help = "Sets a viewer's currency to an amount"
    group = "Currency"

    def __init__(self, send: Send) -> None:
        super().__init__(send)
        self.options = {"currency": self.currency_names, "platform": _viewer_platforms}

    async def run(self, currency: str, username: str, amount: int, platform: str = "Twitch") -> None:
        await self._money("PUT", currency, username, platform, Amount=int(amount))
