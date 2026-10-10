from typing import Any

# how a chat trigger matches: (what the editor shows, hint for the text field)
MODES = {"command": ("Command", "e.g. !cat (with or without text after it)"),
         "contains": ("Has word", "e.g. lizard, or several: gay, bl (whole words anywhere in the message)"),
         "pattern": ("Pattern", "* = any text, e.g. !qa * or * lizard *")}


def mode_of(match: dict[str, Any]) -> tuple[str, str]:
    """A chat trigger's match as (mode, the text the streamer typed). Stored as event fields:
    command → {"command": "!cat"}; contains → {"words": "gay, bl"}; pattern → {"message": "..."}."""
    if "command" in match:
        return "command", str(match["command"])
    if "words" in match:
        return "contains", str(match["words"])
    message = str(match.get("message", ""))
    return "pattern", message


def to_match(mode: str, text: str) -> dict[str, str]:
    text = text.strip()
    if mode == "command":
        word = text.split(" ")[0].casefold() if text else ""
        return {"command": word if word.startswith("!") or not word else "!" + word}
    if mode == "contains":
        return {"words": ", ".join(w.strip() for w in text.split(",") if w.strip())}
    return {"message": text}
