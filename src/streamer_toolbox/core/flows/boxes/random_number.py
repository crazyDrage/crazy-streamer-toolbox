import random

from streamer_toolbox.core.interfaces.box import Box


class RandomNumber(Box):
    name = "random"
    label = "Random number"
    help = "A whole random number from lowest to highest (both included), e.g. 1 to 100 for a d100. Each box it " \
           "is wired into gets a number of its own: to use one number twice, save it in a variable first"
    group = "Random"
    flow_only = True
    data_only = True  # no run wire: it runs whenever a box needs its value (his OPEN 92)
    labels = {"lowest": "From", "highest": "To"}

    async def run(self, lowest: int = 1, highest: int = 100) -> int:
        return random.randint(int(lowest), int(highest))
