import json
from pathlib import Path
from typing import Any

DECKS_FILE = Path("json") / "decks_data.json"
IMAGES = "image"  # SAMMI's folder of button pictures

Layout = dict[str, Any]  # {"background": "#rrggbb", "buttons": {button id: {x, y, w, h, color, ...}}}


class DeckLayouts:
    """Where SAMMI puts each button: read (never written) from SAMMI's json/decks_data.json, the file Deck Hopper
    draws from. Positions and sizes are parts of the deck (0..1), colours come as #rrggbb. A deck SAMMI stores
    encrypted has no layout (the board shows it as a list). Read again only when the file changed."""

    def __init__(self) -> None:
        self._read: tuple[Path, float] | None = None
        self._layouts: dict[str, Layout] = {}

    def layouts(self, sammi_folder: str) -> dict[str, Layout]:
        """deck id → its layout; {} when the folder or file isn't there."""
        path = Path(sammi_folder) / DECKS_FILE if sammi_folder else None
        if path is None or not path.is_file():
            return {}
        stamp = (path, path.stat().st_mtime)
        if stamp != self._read:
            self._layouts = self.parse(json.loads(path.read_text(encoding="utf-8")))
            self._read = stamp
        return self._layouts

    @staticmethod
    def images(sammi_folder: str) -> Path | None:
        folder = Path(sammi_folder) / IMAGES if sammi_folder else None
        return folder if folder and folder.is_dir() else None

    @staticmethod
    def parse(data: dict[str, Any]) -> dict[str, Layout]:
        layouts = {}
        for deck in data.get("default", []):
            if not isinstance(deck, dict):  # encrypted
                continue
            layouts[str(deck.get("unique_id", ""))] = {
                "background": color(deck.get("background_color", 4210752)),
                "buttons": {str(b.get("button_id", "")): {
                    "x": float(b.get("x", 0)), "y": float(b.get("y", 0)),
                    "w": float(b.get("width", 0.1)), "h": float(b.get("height", 0.1)),
                    "color": color(b.get("color", 12632256)), "font_color": color(b.get("font_color", 16777215)),
                    "border": float(b.get("border", 0)), "border_color": color(b.get("border_color", 0)),
                    "transparent": bool(b.get("is_transparent")), "image": str(b.get("image") or ""),
                    "stretch": bool(b.get("stretch")), "text": str(b.get("text", ""))}
                    for b in deck.get("button_list", [])}}
        return layouts


def color(value: Any) -> str:
    """SAMMI's colour number (blue-green-red, like GameMaker) as #rrggbb."""
    number = int(float(value or 0))
    return f"#{number & 255:02x}{(number >> 8) & 255:02x}{(number >> 16) & 255:02x}"
