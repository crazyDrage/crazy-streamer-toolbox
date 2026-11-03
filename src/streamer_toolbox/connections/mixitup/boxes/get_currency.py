from streamer_toolbox.connections.mixitup.boxes.mixitup_box import MixitupBox, Send, _viewer_platforms


class GetCurrency(MixitupBox):
    name = "get_currency"
    label = "Get currency"
    help = "How much of a currency (e.g. rats) a viewer has"
    group = "Currency"

    def __init__(self, send: Send) -> None:
        super().__init__(send)
        self.options = {"currency": self.currency_names, "platform": _viewer_platforms}

    async def run(self, currency: str, username: str, platform: str = "Twitch") -> int:
        return await self.get_currency(currency, username, platform)
