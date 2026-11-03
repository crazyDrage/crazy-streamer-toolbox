import asyncio

from streamer_toolbox.core.actions.fixed_choices import fixed_choices
from streamer_toolbox.core.flows.retrigger import ON_RETRIGGER
from streamer_toolbox.core.interfaces.box import Box


class Wait(Box):
    name = "wait"
    label = "Wait"
    help = "Waits, then goes on. If started again: a new start of the flow during the wait (or before it) " \
           "doesn't run the flow again, it starts the wait over or adds the time again, e.g. light on, Wait 2 s, " \
           "light off: every redeem keeps the light on longer. Gives how many times it was stretched"
    group = "Wait"
    options = {"if_started_again": fixed_choices(ON_RETRIGGER)}
    flow_only = True
    retrigger = "if_started_again"
    hints = {"seconds": "How long, e.g. 2 or 0.5",
             "if_started_again": "The flow is started again while it waits: start the 2 s over, or add 2 s more. "
                                 "That start doesn't run the flow a second time"}

    async def run(self, seconds: float = 1.0, if_started_again: str = "nothing") -> int:
        """How many times a new start stretched it (0 for a plain wait)."""
        retrigger = self.started_again()
        if if_started_again not in ON_RETRIGGER:
            raise ValueError(f"unknown 'If started again' {if_started_again!r}; use one of {', '.join(ON_RETRIGGER)}")
        if if_started_again == "nothing" or retrigger is None or not retrigger.open:  # Test run: a plain wait
            await asyncio.sleep(float(seconds))
            return 0
        return await retrigger.wait(float(seconds), if_started_again)
