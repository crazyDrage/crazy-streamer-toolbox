import re
from collections.abc import Awaitable, Callable
from typing import Any

Request = Callable[..., Awaitable[dict[str, Any]]]  # (message type, data) → VTS's answer data
COLORS = {"red": "FF3030", "orange": "FF9900", "yellow": "FFE040", "green": "40D040", "blue": "4080FF",
          "purple": "A050FF", "pink": "FF80C0", "gray": "909090", "black": "202020", "white": "FFFFFF"}
PHYSICS_REPEAT = 4.0  # VTS keeps a physics override up to 5 s: it is sent again before that
PARAMETER_REPEAT = 0.5  # and a fed-in parameter is "lost" after 1 s without data


def rgba(color: Any) -> tuple[int, int, int, int]:
    """A colour name or hex (RRGGBB / RRGGBBAA, # optional) → 0-255 values."""
    text = str(color).strip().lstrip("#")
    text = COLORS.get(text.casefold(), text)
    if len(text) == 6:
        text += "FF"
    try:
        if len(text) != 8:
            raise ValueError
        return tuple(int(text[i:i + 2], 16) for i in range(0, 8, 2))  # type: ignore[return-value]
    except ValueError:
        raise ValueError(f"a colour is a name ({', '.join(COLORS)}) or hex like FF8800, not {color!r}") from None


def _matcher(parts: Any, picked: Any = "") -> dict[str, Any]:
    """Which parts VTS tints: those whose name has one of the words, and the picked ones by their exact name
    (a word would also catch ArtMesh12 for ArtMesh1); neither = the whole model."""
    words = [w.strip() for w in str(parts or "").replace(",", " ").split() if w.strip()]
    names = [n.strip() for n in str(picked or "").split(",") if n.strip()]
    if not words and not names:
        return {"tintAll": True}
    return {"tintAll": False} | ({"nameContains": words} if words else {}) | ({"nameExact": names} if names else {})


def _by_number(name: str) -> list[tuple[int, int | str]]:
    """A sort key that reads the digits in a name as numbers."""
    return [(0, int(piece)) if piece.isdigit() else (1, piece.casefold())
            for piece in re.split(r"(\d+)", name) if piece]


def _fade(fade: Any) -> float:
    return min(max(float(fade), 0.0), 2.0)


async def _color_names() -> list[str]:
    return list(COLORS)


async def _states() -> list[str]:
    return ["on", "off", "toggle"]
