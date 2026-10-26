from typing import Any

from streamer_toolbox.core.data.box_value import to_list
from streamer_toolbox.core.interfaces.box import Box


class JoinListToText(Box):
    name = "join"
    label = "Join list to text"
    help = "Puts the values of a list together into one text, with the separator between them"
    group = "Text"
    flow_only = True

    async def run(self, items: Any, separator: str = ", ") -> str:
        return str(separator).join(str(i) for i in to_list(items))
