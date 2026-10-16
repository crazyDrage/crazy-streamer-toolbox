import copy
import json
import re
from typing import Any

from streamer_toolbox.core.widgets.widget import Widget

PAGE_CODE = "/static/overlay/element.js"  # in the HTML of a widget that is an imported Element
SHOW = "TOOLBOX_ELEMENT.show("
ALERTS = {"follower": "Follow alert", "subscriber": "Subscriber alert", "tip": "Tip alert", "cheer": "Cheer alert",
          "raid": "Raid alert", "communityGiftPurchase": "Gifted subs alert"}
NUMBER = re.compile(r"\s*(-?\d+(?:\.\d+)?)\s*(px|ms|s)?\s*")
TEXTS = ("text", "latestTicker")
SEEN = ("image", "video", *TEXTS)  # the pieces that have a place on the canvas


class ElementSettings:
    """The settings of an imported StreamElements Element (StreamElementsElements) as a form. An Element is one
    settings file in the widget's JS part: states (always there, or an alert for an event), each with pieces
    (texts, pictures, videos, sounds). fields() names what he may want to change as FIELDS in StreamElements'
    widget format, one group per piece, so the form every widget has (WidgetFieldsForm) draws it; with_values()
    writes the changed ones back. Everything else in the file stays as it is.

    A field's key is "<state number>/<piece>/<what>"."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config

    @classmethod
    def of(cls, widget: Widget) -> "ElementSettings | None":
        """The widget's Element settings, or None when it is not an Element (or its JS part was rewritten)."""
        code = widget.js.strip()
        if PAGE_CODE not in widget.html or not code.startswith(SHOW) or ")" not in code:
            return None
        try:
            config = json.loads(code[len(SHOW):code.rindex(")")])
        except ValueError:
            return None
        return cls(config) if isinstance(config, dict) and isinstance(config.get("configStates"), list) else None

    def to_js(self) -> str:
        return f"{SHOW}{json.dumps(self._config, indent=1, ensure_ascii=False)});"

    def fields(self) -> dict[str, dict[str, Any]]:
        found: dict[str, dict[str, Any]] = {}
        for number, state in enumerate(self._config["configStates"]):
            title = _title(state)
            alert = bool(state.get("categoryId"))
            for name, piece in _pieces(state).items():
                group = f"{title} · {name}"
                for what, spec in _piece_fields(piece, alert).items():
                    found[f"{number}/{name}/{what}"] = {**spec, "group": group}
        return found

    def with_values(self, values: dict[str, Any]) -> "ElementSettings":
        """The settings with these fields set (key → value, as fields() names them). Only a value that differs
        from what is there is written, so an untouched "129.72px" stays as StreamElements wrote it."""
        config = copy.deepcopy(self._config)
        now = {key: spec["value"] for key, spec in self.fields().items()}
        for key, value in values.items():
            if key not in now or value is None or value == now[key]:
                continue
            number, name, what = key.split("/", 2)
            _write(_pieces(config["configStates"][int(number)])[name], what, value)
        return ElementSettings(config)


def _title(state: dict[str, Any]) -> str:
    kind, name = state.get("categoryId"), str(state.get("displayName") or state.get("referenceId") or "State")
    if not kind:
        return name
    return ALERTS.get(kind, f"{kind} alert") + ("" if name == "Default" else f" ({name})")


def _pieces(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    pieces = (state.get("settings") or {}).get("compositeFields")
    return pieces if isinstance(pieces, dict) else {}


def _piece_fields(piece: dict[str, Any], alert: bool) -> dict[str, dict[str, Any]]:
    kind, style = piece.get("type"), piece.get("style") or {}
    fields: dict[str, dict[str, Any]] = {}
    if kind in TEXTS:
        fields["text"] = {"type": "textarea", "label": "Text ({…} is filled in: leave those as they are)",
                          "value": "\n".join(str(line.get("content") or "") for line in piece.get("text") or [])}
        if _number(style.get("fontSize")) is not None:
            fields["size"] = {"type": "number", "label": "Text size", "value": _number(style["fontSize"]), "min": 1}
        if "color" in style:
            fields["color"] = {"type": "colorpicker", "label": "Text colour", "value": style["color"]}
        if "color" in (piece.get("highlightedStyle") or {}):
            fields["highlight"] = {"type": "colorpicker", "label": "Colour of the filled-in words",
                                   "value": piece["highlightedStyle"]["color"]}
    if kind in ("video", "audio") and isinstance(piece.get("volume"), (int, float)):
        fields["volume"] = {"type": "slider", "label": "Volume (%)", "value": round(piece["volume"] * 100),
                            "min": 0, "max": 100, "step": 5}
    if kind == "audio" and isinstance(piece.get("delaySeconds"), (int, float)):
        fields["delay"] = {"type": "number", "label": "Starts after (seconds)", "value": piece["delaySeconds"],
                           "min": 0, "step": 0.1}
    stays = _number(((piece.get("animation") or {}).get("static") or {}).get("animationDuration"))
    if stays is not None and (alert or kind == "latestTicker"):
        fields["stays"] = {"type": "number", "min": 0, "step": 0.1, "value": stays,
                           "label": "One round takes (seconds)" if kind == "latestTicker" else "Stays (seconds)"}
    if kind in SEEN:
        for side, label in (("left", "From the left"), ("top", "From the top")):
            if _number(style.get(side)) is not None:
                fields[side] = {"type": "number", "label": label, "value": _number(style[side])}
    return fields


def _write(piece: dict[str, Any], what: str, value: Any) -> None:
    if what == "text":
        piece["text"] = [{**(piece.get("text") or [{}])[0], "content": str(value)}]
    elif what == "size":
        piece["style"]["fontSize"] = f"{_plain(value)}px"
    elif what == "color":
        piece["style"]["color"] = str(value)
    elif what == "highlight":
        piece["highlightedStyle"]["color"] = str(value)
    elif what == "volume":
        piece["volume"] = max(0.0, min(float(value) / 100, 1.0))
    elif what == "delay":
        piece["delaySeconds"] = max(float(value), 0)
    elif what == "stays":
        piece["animation"]["static"]["animationDuration"] = f"{_plain(max(float(value), 0))}s"
    elif what in ("left", "top"):
        piece["style"][what] = f"{_plain(value)}px"


def _number(text: Any) -> float | int | None:
    """"20px" → 20, "0.15s" → 0.15, "300ms" → 0.3; None for anything else (auto, 50%, nothing)."""
    found = NUMBER.fullmatch(str(text)) if text is not None else None
    if not found:
        return None
    number = float(found.group(1)) / (1000 if found.group(2) == "ms" else 1)
    return int(number) if number.is_integer() else round(number, 4)


def _plain(value: Any) -> str:
    number = float(value)
    return str(int(number)) if number.is_integer() else f"{number:.4f}".rstrip("0")
