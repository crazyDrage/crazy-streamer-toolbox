from streamer_toolbox.connections.mixitup.boxes.mixitup_box import MixitupBox, Send


class GetCounter(MixitupBox):
    name = "get_counter"
    label = "Get counter"
    help = "A Mix It Up counter's value"
    group = "Counters"

    def __init__(self, send: Send) -> None:
        super().__init__(send)
        self.options = {"counter": self.counter_names}

    async def run(self, counter: str) -> float:
        return await self.get_counter(counter)
