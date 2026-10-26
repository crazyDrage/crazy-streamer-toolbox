from streamer_toolbox.connections.mixitup.boxes.mixitup_box import MixitupBox, Send, _amount, _viewer_platforms


class GetItem(MixitupBox):
    name = "get_item"
    label = "Get item"
    help = "How many of an inventory item a viewer has"
    group = "Inventory"
    hints = {"item": "inventory · item"}

    def __init__(self, send: Send) -> None:
        super().__init__(send)
        self.options = {"item": self.item_names, "platform": _viewer_platforms}

    async def run(self, item: str, username: str, platform: str = "Twitch") -> int:
        return _amount(await self._send("GET", await self._item_path(item, username, platform)))
