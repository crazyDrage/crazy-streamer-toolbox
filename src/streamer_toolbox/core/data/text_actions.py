import re
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.box_value import to_bool, to_list

CASES = ["upper", "lower", "title"]


class TextActions:
    """Text boxes (SAMMI's String commands): split a chat message into words, join, replace, length, case."""

    def add_to(self, actions: ActionRegistry) -> None:
        async def cases() -> list[str]:
            return CASES

        actions.add("text.split", self.split, "Cuts text into a list at each separator (empty = at spaces), e.g. "
                    "a redeem message 'll 5' → ['ll', '5']. Empty pieces are left out", "Split text",
                    group="Text", flow_only=True)
        actions.add("text.join", self.join, "Puts the values of a list together into one text, with the "
                    "separator between them", "Join list to text", group="Text", flow_only=True)
        actions.add("text.replace", self.replace, "Replaces every 'find' in the text", "Replace in text",
                    group="Text", flow_only=True)
        actions.add("text.length", self.length, "How many characters the text has", "Text length", group="Text",
                    flow_only=True)
        actions.add("text.case", self.case, "UPPER, lower or Title Case", "Change case", group="Text",
                    options={"to": cases}, flow_only=True)
        actions.add("text.trim", self.trim, "Takes away spaces (and line breaks) at the start and the end",
                    "Trim text", group="Text", flow_only=True)

    @staticmethod
    async def split(text: str, separator: str = "") -> list[str]:
        parts = str(text).split(separator) if separator else str(text).split()
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    async def join(items: Any, separator: str = ", ") -> str:
        return str(separator).join(str(i) for i in to_list(items))

    @staticmethod
    async def replace(text: str, find: str, replace_with: str = "", ignore_case: bool = False) -> str:
        if not find:
            raise ValueError("find is empty")
        flags = re.IGNORECASE if to_bool(ignore_case) else 0
        return re.sub(re.escape(str(find)), lambda _: str(replace_with), str(text), flags=flags)

    @staticmethod
    async def length(text: str) -> int:
        return len(str(text))

    @staticmethod
    async def case(text: str, to: str = "lower") -> str:
        if to not in CASES:
            raise ValueError(f"to must be one of {', '.join(CASES)}, not {to!r}")
        return {"upper": str.upper, "lower": str.lower, "title": str.title}[to](str(text))

    @staticmethod
    async def trim(text: str) -> str:
        return str(text).strip()
