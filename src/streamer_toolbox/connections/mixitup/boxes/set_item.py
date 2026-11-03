from streamer_toolbox.connections.mixitup.boxes.mixitup_box import MixitupBox, Send, _viewer_platforms


class SetItem(MixitupBox):
    name = "set_item"
    label = "Set item"
    help = "Sets how many of an item a viewer has"
    group = "Inventory"
    hints = {"item": "inventory · item"}

    def __init__(self, send: Send) -> None:
        super().__init__(send)
        self.options = {"item": self.item_names, "platform": _viewer_platforms}

    async def run(self, item: str, username: str, amount: int, platform: str = "Twitch") -> None:
        await self._send("PUT", await self._item_path(item, username, platform), json={"Amount": int(amount)})
