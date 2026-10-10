import json
import math
import random
import re
from datetime import datetime
from typing import Any, Optional

HTTP_REQUEST = 169.0  # SAMMI command id of "HTTP Request"
GREY = 12632256.0     # SAMMI colours are BGR ints; this is the default button grey
WHITE = 16777215.0
RESULT_VARIABLE = "toolbox_result"


class SammiDeckBuilder:
    """Builds a SAMMI deck (for "Paste Deck") with one button per toolbox action.

    Each button does a single HTTP Request: POST <base_url>/action/<name>. Required action parameters go in the
    body as SAMMI variables of the same name (`/$video_path$/`), so a button can be copied into a redeem that
    sets them. The shape follows crazyDrage's own exports from SAMMI 2025.3.1.
    """

    def __init__(self, base_url: str, deck_name: str = "toolbox", columns: int = 4,
                 now: Optional[datetime] = None, rng: Optional[random.Random] = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._deck_name = deck_name
        self._columns = columns
        self._now = now or datetime.now()
        self._rng = rng or random.Random()

    def build(self, actions: list[dict[str, Any]]) -> dict[str, Any]:
        """actions: the JSON list from GET /actions. Returns the file content (deck_data is a JSON string)."""
        deck_id = self._unique_id()
        rows = max(1, math.ceil(len(actions) / self._columns))
        cell_w, cell_h = 1 / self._columns, min(0.1, 1 / rows)
        buttons = [self._button(a, (i % self._columns) * cell_w, (i // self._columns) * cell_h, cell_w, cell_h)
                   for i, a in enumerate(actions)]
        deck = {
            "background_color": 4210752.0, "on": True, "grid_x": 10.0, "grid_y": 10.0, "snap_grid": 1.0,
            "lb_version": "2025.3.1", "sammi_version": "2025.3.1", "background_image": "", "encrypted": False,
            "adaptive_resizing": 1.0, "unique_id": deck_id, "deck_name": self._deck_name, "stretch": 0.0,
            "button_list": buttons,
        }
        return {"deck_data": json.dumps(deck), "unique_id": deck_id, "include_image": {}}

    def _button(self, action: dict[str, Any], x: float, y: float, w: float, h: float) -> dict[str, Any]:
        name = action["name"]
        return {
            "button_id": button_id(name), "text": action.get("label") or name, "x": round(x, 4), "y": round(y, 4),
            "width": round(w * 0.95, 4), "height": round(h * 0.9, 4),
            "color": GREY, "font_color": WHITE, "font_shadow": 1.0, "border": 2.0, "border_color": 0.0,
            "image": "", "is_transparent": 0.0, "stretch": 0.0, "deck": 0.0, "functions": 65.0,
            "group_id": "", "init_variable": "", "overlappable": 0.0, "payload": 0.0, "persistent": 1.0,
            "press_type": 0.0, "queueable": 0.0, "button_duration": 0.0, "release_duration": 0.0,
            "release_list": [], "switch_deck": "", "triggers": [],
            "command_list": [self._http_request(action)],
        }

    def _http_request(self, action: dict[str, Any]) -> dict[str, Any]:
        required = [p["name"] for p in action.get("params", []) if p["required"]]
        # SAMMI replaces /$var$/ inside the string before sending
        body = json.dumps({p: f"/${p}$/" for p in required}) if required else ""
        return {
            "cmd": HTTP_REQUEST, "obsid": "Main", "pos": 0.0, "vis": 1.0, "ms": 0.0, "sel": 0.0, "dis": 0.0,
            "xpan": 0.0, "async": 0.0,
            "b0": f"{self._base_url}/action/{action['name']}", "b1": "POST", "b2": "", "b3": body,
            "b4": RESULT_VARIABLE,
        }

    def _unique_id(self) -> str:
        # same shape as SAMMI's own ids: timestamp to the millisecond plus random digits
        stamp = self._now.strftime("%Y%m%d%H%M%S") + f"{self._now.microsecond // 1000:03d}"
        return stamp + "".join(str(self._rng.randrange(10)) for _ in range(6))


def button_id(action_name: str) -> str:
    return "tb_" + re.sub(r"[^A-Za-z0-9_]", "_", action_name)
