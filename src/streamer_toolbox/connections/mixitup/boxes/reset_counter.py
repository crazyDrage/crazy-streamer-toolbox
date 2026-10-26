from streamer_toolbox.connections.mixitup.boxes.mixitup_box import MixitupBox, Send, _part


class ResetCounter(MixitupBox):
    name = "reset_counter"
    label = "Reset counter"
    help = "Sets a counter back to 0"
    group = "Counters"

    def __init__(self, send: Send) -> None:
        super().__init__(send)
        self.options = {"counter": self.counter_names}

    async def run(self, counter: str) -> None:
        await self._send("POST", f"counters/{_part(counter)}/reset")
