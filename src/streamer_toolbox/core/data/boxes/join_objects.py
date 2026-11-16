import copy
from typing import Any

from streamer_toolbox.core.data.boxes.object_shared import _object
from streamer_toolbox.core.interfaces.box import Box


class JoinObjects(Box):
    """Two objects in one (his 11-16: "I would do a different dict, and then add the 2 dicts together"), e.g. the
    BetterTTV emotes' emoji dictionary and Twitch emotes' into the one an event gets. A key both have gets the
    second one's value."""

    name = "join"
    data_only = True  # no run wire: only works out a value from its inputs (his rule, round 62 A / notes 10-29)
    label = "Join objects"
    help = "Both objects in one: every key of the first and of the second. A key both have gets the second's " \
           "value. An empty field is an empty object"
    group = "Change"
    flow_only = True
    labels = {"first": "First object", "second": "Second object"}
    hints = {"second": "Its values win where both have the same key"}

    async def run(self, first: Any = None, second: Any = None) -> dict[str, Any]:
        return {**copy.deepcopy(_object(first)), **copy.deepcopy(_object(second))}
