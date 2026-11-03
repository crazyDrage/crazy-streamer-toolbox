from typing import Any


def names_in(text: Any) -> list[str]:
    """The names typed into a box's output_names field ("text, count" → ["text", "count"]): commas or new lines
    between them, spaces around them left out, each one once."""
    if not isinstance(text, str):
        return []
    found: list[str] = []
    for name in text.replace("\n", ",").split(","):
        name = name.strip()
        if name and name not in found:
            found.append(name)
    return found
