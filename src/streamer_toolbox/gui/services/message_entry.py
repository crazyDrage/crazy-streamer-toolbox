from dataclasses import dataclass


@dataclass(frozen=True)
class MessageEntry:
    """One line of the Debug list: a message the toolbox showed, a flow run or a box error."""

    time: str   # "22:41:07"
    kind: str   # "positive", "negative", "warning", "info", "ongoing" or "run" (a flow or action that ran fine)
    text: str
