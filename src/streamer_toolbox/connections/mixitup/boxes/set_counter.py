from streamer_toolbox.connections.mixitup.boxes.mixitup_box import MixitupBox, Send, _part


class SetCounter(MixitupBox):
    name = "set_counter"
    label = "Set counter"
    help = "Sets a counter to a value (makes it if it's new)"
    group = "Counters"

    def __init__(self, send: Send) -> None:
        super().__init__(send)
        self.options = {"counter": self.counter_names}

    async def run(self, counter: str, amount: float) -> None:
        if counter not in await self.counter_names():
            await self._send("POST", "counters", json={"Name": counter})
        await self._send("POST", f"counters/{_part(counter)}/set", json={"Amount": float(amount)})
