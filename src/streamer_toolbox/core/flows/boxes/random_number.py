import random

from streamer_toolbox.core.interfaces.box import Box


class RandomNumber(Box):
    name = "random"
    label = "Random number"
    help = "A whole random number from lowest to highest (both included), e.g. 1 to 100 for a d100. It picks once, " \
           "where its run wire reaches it: every box it is wired into gets that same number"
    group = "Random"
    flow_only = True
    # a run wire (his round 67): without one, each box that reads it would get a number of its own
    labels = {"lowest": "From", "highest": "To"}

    async def run(self, lowest: int = 1, highest: int = 100) -> int:
        return random.randint(int(lowest), int(highest))
