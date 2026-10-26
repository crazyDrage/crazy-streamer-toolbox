import asyncio
from collections.abc import AsyncIterator

from streamer_toolbox.core.actions.fixed_choices import fixed_choices
from streamer_toolbox.core.flows.box_signals import ON_ALREADY_RUNNING, ONE
from streamer_toolbox.core.interfaces.box import Box

SHORTEST_PAUSE = 0.05  # between rounds: a round of quick boxes can't take the toolbox over


class Loop(Box):
    name = "loop"
    label = "Loop (start / stop)"
    help = "Runs what's wired to 'each' again and again, one round after the other, until a wire reaches its " \
           "'stop' dot (e.g. the same button pressed again, through a flow input start / stop). Then 'stopped' " \
           "goes on. A second start while it loops does nothing, or runs a loop of its own alongside (Started again " \
           "while it loops). A wire into 'switch' stops it if it loops, else starts it (one button for on and off). Its orange dot 'round' counts the rounds: 1, 2, 3, ..."
    group = "Repeat"
    ports = ("each", "stopped")
    flow_only = True
    entries = ("stop", "switch")
    toggles = ("switch",)
    labels = {"pause": "Pause between rounds (s)", "if_already_looping": "Started again while it loops"}
    options = {"if_already_looping": fixed_choices(ON_ALREADY_RUNNING)}
    alongside = "if_already_looping"
    outputs = {"round": "number"}
    hints = {"rounds": "0 = until stopped; else stop after this many rounds",
             "pause": "Waits this long after each round. A stop ends the loop after the round that's running. The "
                      "flow must Run alongside (top of the page), so the stop can get in",
             "if_already_looping": "Only one: a start of the flow that reaches the Loop while it loops stops there "
                                   "(a timer that only gets longer). Another one alongside: each start loops on "
                                   "its own (each redeem throws its own items); a stop from a run stops its own "
                                   "loop, from a run without one every loop"}

    async def run(self, rounds: int = 0, pause: float = 0.0,
                  if_already_looping: str = ONE) -> AsyncIterator[str | tuple[str, dict[str, int]]]:
        """Hands the runner one round at a time until its stop or switch dot gets a wire (or the rounds are
        done)."""
        rounds, pause = int(rounds or 0), max(float(pause or 0), SHORTEST_PAUSE)
        signals = self.signals()  # None on its own (Test box): then it only counts rounds

        async def go() -> AsyncIterator[str | tuple[str, dict[str, int]]]:
            done = 0
            while not (signals and signals.has("stop", "switch")):
                yield "each", {"round": done + 1}  # the round's number, its orange dot while the round runs
                done += 1
                if 0 < rounds <= done:
                    break
                if signals:
                    await signals.wait_for(pause, "stop", "switch")
                else:
                    await asyncio.sleep(pause)
            yield "stopped"

        return go()
