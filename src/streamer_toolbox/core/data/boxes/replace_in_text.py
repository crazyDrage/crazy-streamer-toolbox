import re

from streamer_toolbox.core.data.box_value import to_bool
from streamer_toolbox.core.interfaces.box import Box


class ReplaceInText(Box):
    name = "replace"
    label = "Replace in text"
    help = "Replaces every 'find' in the text"
    group = "Text"
    flow_only = True

    async def run(self, text: str, find: str, replace_with: str = "", ignore_case: bool = False) -> str:
        if not find:
            raise ValueError("find is empty")
        flags = re.IGNORECASE if to_bool(ignore_case) else 0
        return re.sub(re.escape(str(find)), lambda _: str(replace_with), str(text), flags=flags)
