import asyncio
from typing import Any

from streamer_toolbox.core.flows.flow import Flow


class FlowRun:
    """What one run of a flow carries along: its event and inputs, the results so far, the first error, and each
    box's latest result for the data wires. A test run (one box on its own) may use results from earlier runs."""

    def __init__(self, flow: Flow, event: dict[str, Any], inputs: dict[str, Any], test: bool = False,
                 ended: asyncio.Future | None = None) -> None:
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
        self.ended = ended  # run as a box in another flow: set (End box name, this run) when an End box is reached

    def fail(self, error: Exception) -> None:
        if self.error is None:
            self.error = error
