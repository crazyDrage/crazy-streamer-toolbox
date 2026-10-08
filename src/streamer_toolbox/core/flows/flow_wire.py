from dataclasses import dataclass

START = "start"  # the id of every flow's Start box; its one port is "out"
DONE = "done"    # the port of a box whose action has no ports of its own


@dataclass(frozen=True)
class FlowWire:
    """"When box `source` leaves through `port`, run box `target`". Several wires from one port run their
    targets at the same time (in parallel); an If box has the ports "then" and "else". `entry` names the
    target's extra run dot it ends at (a Loop's "stop"); empty = its normal run dot."""

    source: str
    port: str
    target: str
    entry: str = ""
