import asyncio
from typing import Any

from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_wire import START


class FlowRun:
    """What one run of a flow carries along: its event and inputs, the results so far, the first error, and each
    box's latest result for the data wires. A test run (one box on its own) may use results from earlier runs."""

    def __init__(self, flow: Flow, event: dict[str, Any], inputs: dict[str, Any], test: bool = False,
                 ended: asyncio.Future | None = None, start: str = START) -> None:
        self.flow = flow
        self.event = event
        self.inputs = inputs
        self.results: list[dict[str, Any]] = []
        self.error: Exception | None = None
        self.count = 0
        self.arrivals: dict[str, int] = {}  # box id → wires arrived so far (Wait for all)
        self.values: dict[str, Any] = {}  # box id → its latest result in this run (data wires read it)
        self.pulling: set[str] = set()  # boxes running because a data wire needs them (catches a loop)
        self.outputs: dict[str, Any] = {}  # what its Flow output boxes gave, by name
        self.test = test
        self.ended = ended  # run as a box in another flow: set (to this run) when the End box is reached
        self.start = start  # the Start box it started at (a trigger's id, or Manual)
        self.stopped = False  # stopped by hand (FlowRunner.stop)

    def fail(self, error: Exception) -> None:
        if self.error is None:
            self.error = error
