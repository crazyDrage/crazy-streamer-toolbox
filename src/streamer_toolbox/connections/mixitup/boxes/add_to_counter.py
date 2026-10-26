from streamer_toolbox.connections.mixitup.boxes.mixitup_box import MixitupBox, Send, _part


class AddToCounter(MixitupBox):
    name = "add_to_counter"
    label = "Add to counter"
    help = "Adds to a counter (a minus number takes away)"
    group = "Counters"

    def __init__(self, send: Send) -> None:
        super().__init__(send)
        self.options = {"counter": self.counter_names}

    async def run(self, counter: str, amount: float = 1) -> float:
        await self._send("POST", f"counters/{_part(counter)}/update", json={"Amount": float(amount)})
        return await self.get_counter(counter)
