from streamer_toolbox.core.interfaces.box import Box


class Repeat(Box):
    name = "repeat"
    label = "Repeat"
    help = "Runs what's wired to 'each' this many times, one after the other, then goes on through 'done'"
    group = "Repeat"
    ports = ("each", "done")
    flow_only = True
    labels = {"times": "How many times"}

    async def run(self, times: int = 2) -> list[str]:
        return ["each"] * max(int(times), 0) + ["done"]
