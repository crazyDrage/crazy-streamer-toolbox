from streamer_toolbox.connections.mixitup.boxes.mixitup_box import MixitupBox, Send, _viewer_platforms


class AddItem(MixitupBox):
    name = "add_item"
    label = "Add item"
    help = "Gives a viewer items (a minus number takes them away)"
    group = "Inventory"
    hints = {"item": "inventory · item"}

    def __init__(self, send: Send) -> None:
        super().__init__(send)
        self.options = {"item": self.item_names, "platform": _viewer_platforms}

    async def run(self, item: str, username: str, amount: int = 1, platform: str = "Twitch") -> None:
        await self._send("PATCH", await self._item_path(item, username, platform), json={"Amount": int(amount)})
