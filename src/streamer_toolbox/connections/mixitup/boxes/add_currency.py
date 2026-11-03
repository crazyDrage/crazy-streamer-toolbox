from streamer_toolbox.connections.mixitup.boxes.mixitup_box import MixitupBox, Send, _viewer_platforms


class AddCurrency(MixitupBox):
    name = "add_currency"
    label = "Add currency"
    help = "Gives a viewer some currency (a minus number takes it away)"
    group = "Currency"

    def __init__(self, send: Send) -> None:
        super().__init__(send)
        self.options = {"currency": self.currency_names, "platform": _viewer_platforms}

    async def run(self, currency: str, username: str, amount: int, platform: str = "Twitch") -> int:
        await self._money("PATCH", currency, username, platform, Amount=int(amount))
        return await self.get_currency(currency, username, platform)
