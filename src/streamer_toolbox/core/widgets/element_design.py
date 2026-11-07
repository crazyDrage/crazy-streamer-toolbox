import copy
import json
import re
import uuid
from typing import Any

from streamer_toolbox.core.widgets.element_settings import ALERTS, SHOW, _number, _plain, element_config
from streamer_toolbox.core.widgets.widget import Widget

# the page of a designed widget is the page of an imported Element: element.js draws it from its settings
HTML = '<div id="toolbox-element"></div>\n<script src="/static/overlay/element.js"></script>'
CANVAS = (1920, 1080)
KINDS = {"text": "Text", "image": "Picture or GIF", "video": "Video", "audio": "Sound", "shape": "Shape",
         "goal": "Goal bar", "latestTicker": "Recent names"}
# what a goal bar can count (a key of the session data, "<kind>-<what>.<count or amount>")
GOALS = {"follower-session.count": "Followers this stream", "subscriber-session.count": "Subs this stream",
         "cheer-session.amount": "Bits this stream", "tip-session.amount": "Tips this stream",
         "raid-session.count": "Raids this stream", "follower-month.count": "Followers this month",
         "subscriber-month.count": "Subs this month", "cheer-month.amount": "Bits this month",
         "follower-total.count": "Followers in all", "subscriber-total.count": "Subs in all",
         "subscriber-points.amount": "Sub points"}
# whose names a ticker shows (the session data's "<kind>-recent"), and how
TICKERS = {"follower": "Followers", "subscriber": "Subs", "cheer": "Cheers", "raid": "Raiders", "tip": "Tips"}
TICKER_LOOKS = {"run": "Runs along", "still": "In a row", "lines": "One per line"}
# what an alert's amount is, per event (a variation: "only from 100 bits")
AMOUNTS = {"subscriber": "months", "communityGiftPurchase": "gifted subs", "cheer": "bits", "raid": "viewers",
           "tip": "amount"}
SUGGESTED = {"subscriber": 12, "communityGiftPurchase": 5, "cheer": 100, "raid": 10, "tip": 10}
# a new text of an alert says what happened
ALERT_TEXTS = {"follower": "{event.data.username} followed!", "subscriber": "{event.data.username} subscribed!",
               "communityGiftPurchase": "{event.data.username} gifted {event.data.amount} subs!",
               "cheer": "{event.data.username} cheered {event.data.amount} bits!",
               "raid": "{event.data.username} raids with {event.data.amount} viewers!",
               "tip": "{event.data.username} tipped {event.data.currency}{event.data.amount}!"}
AMOUNT = {"var": "event.data.amount"}
CHANCE = {"var": "random"}  # element.js: a number from 0 to 1, new for each event
KIND_OF = re.compile(r"session\.\w+\.(follower|subscriber|cheer|raid|tip)-")
# an alert layer's event: categoryId → the event.type element.js gives it (elementEvent)
EVENTS = {"follower": "follow", "subscriber": "subscriber", "communityGiftPurchase": "communityGiftPurchase",
          "cheer": "cheer", "raid": "raid", "tip": "tip"}
# how a piece comes in and goes out: the names of the alert editor (alerts.css), element.js plays them
ANIMATIONS_IN = {"": "Just there", "fade": "Fade in", "slide_down": "Slide in from above",
                 "slide_up": "Slide in from below", "slide_left": "Slide in from the right",
                 "slide_right": "Slide in from the left", "zoom": "Grow", "pop": "Pop"}
ANIMATIONS_OUT = {"": "Just gone", "fade": "Fade out", "slide_up": "Slide out upwards",
                  "slide_down": "Slide out downwards", "slide_left": "Slide out to the left",
                  "slide_right": "Slide out to the right", "zoom": "Shrink"}
# what a piece that is always there does when an event comes (his "animation on follow")
REACTIONS = {"pop": "Pop", "shake": "Shake", "jump": "Jump", "pulse": "Pulse", "spin": "Spin", "flash": "Flash"}
ENDINGS = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
           ".webp": "image/webp", ".svg": "image/svg+xml", ".apng": "image/apng",
           ".webm": "video/webm", ".mp4": "video/mp4",
           ".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".wav": "audio/wav", ".m4a": "audio/mp4"}
NUMBERED = re.compile(r"(.*?)\s*(\d+)$")


class ElementDesign:
    """A widget as the widget editor (Overlay → Widget editor) changes it: the settings of a StreamElements
    "Element" (element.js draws them), so an imported Element opens in the editor too. Layers are the Element's
    states, named by him: always there (labels such as "latest follower", pictures, goal bars) or an alert for
    an event (follow, sub, ...), several for one event with a condition of their own (a variation: from 100
    bits on). Each is a list of pieces (texts, pictures and GIFs, videos, sounds, shapes, goal bars, tickers)
    drawn bottom to top. A piece's place and look are CSS in pixels on the canvas (its `style`), as
    StreamElements keeps them.

    The editor's own additions, which StreamElements doesn't know (element.js plays them): the alert editor's
    animations as `animationName`; on a piece `toolbox.react` (what a piece that is always there does when an
    event comes: {events, animation, seconds}), `toolbox.goal` and `toolbox.ticker`; on a layer `toolbox.off`
    and `toolbox.front`; the shape and goal kinds of piece."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    @classmethod
    def new(cls) -> "ElementDesign":
        width, height = CANVAS
        return cls({"boundingBox": {"width": width, "height": height}, "configStates": [_layer("static")]})

    @classmethod
    def of(cls, widget: Widget) -> "ElementDesign | None":
        """The widget's design; None when it is no Element (custom widget code)."""
        config = element_config(widget)
        return None if config is None else cls(config)

    def copy(self) -> "ElementDesign":
        return ElementDesign(copy.deepcopy(self.config))

    def to_js(self) -> str:
        """The JS part. It marks the settings as the editor's (toolbox.top_first): of two variations that both
        fit, element.js then plays the one the editor shows on top. An imported Element nobody saved here keeps
        StreamElements' order (the first in the list)."""
        self.config.setdefault("toolbox", {})["top_first"] = True
        return f"{SHOW}{json.dumps(self.config, indent=1, ensure_ascii=False)});"

    def canvas(self) -> tuple[int, int]:
        box = self.config.get("boundingBox") or {}
        return int(box.get("width") or CANVAS[0]), int(box.get("height") or CANVAS[1])

    # layers

    def set_canvas(self, width: int, height: int) -> None:
        """The widget's size (OBS's Browser source should have the same); the pieces stay where they are."""
        self.config["boundingBox"] = {**(self.config.get("boundingBox") or {}),
                                      "width": max(50, min(int(width), 7680)),
                                      "height": max(50, min(int(height), 4320))}

    # layers

    def layers(self) -> list[tuple[int, str]]:
        """(number, title) of each layer, in their order. An alert's title names its event when its own name
        doesn't ("Big ones (Cheer alert)")."""
        return [(number, self._layer_title(number)) for number in range(len(self.config["configStates"]))]

    def layer_name(self, layer: int) -> str:
        """The name he gave it; a StreamElements alert's "Default" reads as its event's ("Follow alert")."""
        state = self._state(layer)
        name = " ".join(str(state.get("displayName") or "").split())
        event = state.get("categoryId")
        if event and name in ("", "Default"):
            return ALERTS.get(event, f"{event} alert")
        return name or ("Always there" if not event else ALERTS.get(event, f"{event} alert"))

    def event_of(self, layer: int) -> str:
        """The layer's event (categoryId, e.g. follower), "" for one that is always there."""
        return str(self._state(layer).get("categoryId") or "")

    def add_layer(self, event: str = "", name: str = "") -> int:
        """A new, empty layer at the end: always there (event "") or an alert. A second alert for an event
        is a variation: it gets a condition (only from 100 bits; a follow by chance), else the first plays."""
        if event and event not in EVENTS:
            raise ValueError(f"no alert for {event!r}")
        states = self.config["configStates"]
        plain = event and any(s.get("categoryId") == event and not _has_own_condition(s) and self._on(s)
                              for s in states)
        state = _layer(event or "static")
        state["referenceId"] = str(uuid.uuid4())
        wanted = " ".join(str(name).split()) or (ALERTS[event] if event else "Layer")
        state["displayName"] = _free(wanted, {self.layer_name(n) for n in range(len(states))})
        states.append(state)
        number = len(states) - 1
        if plain:
            self.set_condition(number, **({"at_least": SUGGESTED[event]} if event in SUGGESTED else {"chance": 50}))
        return number

    def add_alert(self, event: str) -> int:
        """The layer for this event (follower, subscriber, ...): the one there is, or a new, empty one."""
        if event not in EVENTS:
            raise ValueError(f"no alert for {event!r}")
        for number, state in enumerate(self.config["configStates"]):
            if state.get("categoryId") == event and not _has_own_condition(state):
                return number
        return self.add_layer(event)

    def rename_layer(self, layer: int, new: str) -> str:
        new = " ".join(str(new).split())
        if not new or new == self.layer_name(layer):
            return self.layer_name(layer)
        if new in {self.layer_name(n) for n in range(len(self.config["configStates"])) if n != layer}:
            raise ValueError(f"there's a layer {new!r} already")
        self._state(layer)["displayName"] = new
        return new

    def remove_layer(self, layer: int) -> None:
        self._state(layer)
        if len(self.config["configStates"]) == 1:
            raise ValueError("a widget keeps one layer at least (it can be empty)")
        del self.config["configStates"][layer]

    def duplicate_layer(self, layer: int) -> int:
        """A copy of the layer and its pieces right after it; its number."""
        twin = copy.deepcopy(self._state(layer))
        twin["referenceId"] = str(uuid.uuid4())
        twin["displayName"] = _free(self.layer_name(layer),
                                    {self.layer_name(n) for n in range(len(self.config["configStates"]))})
        self.config["configStates"].insert(layer + 1, twin)
        return layer + 1

    def move_layer(self, layer: int, step: int) -> int:
        """+1: later in the list (drawn in front; of the alerts for an event that fit, the last plays), -1:
        earlier; its new number."""
        states = self.config["configStates"]
        state = states.pop(layer)
        at = max(0, min(layer + step, len(states)))
        states.insert(at, state)
        return at

    def set_layer_event(self, layer: int, event: str) -> None:
        """Makes it an alert for another event, or ("") a layer that is always there. Its own condition (a
        variation's) stays; a name that was only the old event's ("Follow alert") follows."""
        if event and event not in EVENTS:
            raise ValueError(f"no alert for {event!r}")
        state = self._state(layer)
        old = self.event_of(layer)
        if old == event:
            return
        auto = self.layer_name(layer) in (ALERTS.get(old), "Always there")
        own = [trigger.get("userCondition") or {} for trigger in state.get("triggers") or []] or [{}]
        fresh = _layer(event or "static")
        state["categoryId"] = fresh["categoryId"]
        state["triggers"] = [{"systemCondition": fresh["triggers"][0]["systemCondition"],
                              "userCondition": own[0] if event else {}}]
        if auto:
            others = {self.layer_name(n) for n in range(len(self.config["configStates"])) if n != layer}
            state["displayName"] = _free(ALERTS[event] if event else "Always there", others)

    def is_on(self, layer: int) -> bool:
        return self._on(self._state(layer))

    def set_on(self, layer: int, on: bool) -> None:
        """A layer that is off isn't shown on stream (its alert doesn't play); it stays in the editor."""
        self._own(self._state(layer), "off", None if on else True)

    def in_front(self, layer: int) -> bool:
        """A layer that is always there is drawn in front of the alerts (else behind them)."""
        state = self._state(layer)
        front = (state.get("toolbox") or {}).get("front")
        return bool(front) if front is not None else state.get("referenceId") == "foreground"

    def set_in_front(self, layer: int, front: bool) -> None:
        self._own(self._state(layer), "front", bool(front))

    def condition(self, layer: int) -> dict[str, Any]:
        """An alert's own condition (a variation): {at_least, at_most: its amount (bits, months, ...) or None,
        chance: percent or None, other: a condition of StreamElements' this editor doesn't know (kept)}."""
        found: dict[str, Any] = {"at_least": None, "at_most": None, "chance": None, "other": False}
        for part in self._condition_parts(layer):
            if _is(part, ">=", AMOUNT):
                found["at_least"] = part[">="][1]
            elif _is(part, "<=", AMOUNT):
                found["at_most"] = part["<="][1]
            elif _is(part, "<", CHANCE):
                found["chance"] = round(float(part["<"][1]) * 100, 2)
            else:
                found["other"] = True
        return found

    def set_condition(self, layer: int, **changes: Any) -> None:
        """Changes some of condition()'s at_least, at_most, chance (None: not asked)."""
        if not self.event_of(layer):
            raise ValueError("only an alert has a condition")
        now = {**self.condition(layer), **changes}
        parts = [part for part in self._condition_parts(layer)
                 if not (_is(part, ">=", AMOUNT) or _is(part, "<=", AMOUNT) or _is(part, "<", CHANCE))]
        if now["at_least"] is not None:
            parts.append({">=": [AMOUNT, _plain_number(now["at_least"])]})
        if now["at_most"] is not None:
            parts.append({"<=": [AMOUNT, _plain_number(now["at_most"])]})
        if now["chance"] is not None:
            parts.append({"<": [CHANCE, round(max(0.0, min(float(now["chance"]), 100.0)) / 100, 4)]})
        rule = {} if not parts else parts[0] if len(parts) == 1 else {"and": parts}
        for trigger in self._state(layer).setdefault("triggers", [{"systemCondition": {}}]):
            trigger["userCondition"] = rule

    def _condition_parts(self, layer: int) -> list[Any]:
        triggers = self._state(layer).get("triggers") or [{}]
        rule = triggers[0].get("userCondition") or {}
        if not rule:
            return []
        return list(rule["and"]) if list(rule) == ["and"] and isinstance(rule["and"], list) else [rule]

    def _layer_title(self, layer: int) -> str:
        name, event = self.layer_name(layer), self.event_of(layer)
        alert = ALERTS.get(event, f"{event} alert")
        if not event or alert.split()[0].casefold() in name.casefold():
            return name
        return f"{name} ({alert})"

    @staticmethod
    def _on(state: dict[str, Any]) -> bool:
        return not (state.get("toolbox") or {}).get("off")

    @staticmethod
    def _own(state: dict[str, Any], key: str, value: Any) -> None:
        """The editor's own setting of a layer (StreamElements doesn't know it); None takes it away."""
        own = state.setdefault("toolbox", {})
        if value is None:
            own.pop(key, None)
        else:
            own[key] = value
        if not own:
            state.pop("toolbox", None)

    # pieces

    def pieces(self, layer: int) -> dict[str, dict[str, Any]]:
        settings = self._state(layer).setdefault("settings", {})
        if not isinstance(settings.get("compositeFields"), dict):
            settings["compositeFields"] = {}
        return settings["compositeFields"]

    def piece(self, layer: int, name: str) -> dict[str, Any]:
        found = self.pieces(layer).get(name)
        if found is None:
            raise KeyError(f"no piece {name!r} in that layer")
        return found

    def add(self, layer: int, kind: str, file: str = "") -> str:
        """A new piece in the middle of the canvas, on top of the others; its name."""
        if kind not in KINDS:
            raise ValueError(f"not a kind of piece: {kind!r}")
        alert = bool(self.event_of(layer))
        width, height = self.canvas()
        piece: dict[str, Any] = {"type": kind, "media": [], "mimeType": f"{kind}/*"}
        if kind == "text":
            piece.update(mimeType="text/multiline", highlightedStyle={"color": "#ffb347"},
                         text=[{"content": ALERT_TEXTS.get(self.event_of(layer), "{event.data.username}") if alert
                                else "Latest follower: {session.twitch.follower-latest.name}"}],
                         style={"left": _px(width / 2 - 300), "top": _px(height / 2 - 30), "width": "600px",
                                "fontSize": "48px", "color": "#ffffff", "fontFamily": "Arial",
                                "fontWeight": "bold", "textAlign": "center",
                                "textShadow": "2px 2px 4px #000000"})
        elif kind in ("image", "video"):
            piece["style"] = {"left": _px(width / 2 - 200), "top": _px(height / 2 - 150), "width": "400px"}
        elif kind == "shape":
            piece.update(mimeType="", style={"left": _px(width / 2 - 200), "top": _px(height / 2 - 100),
                                             "width": "400px", "height": "200px", "backgroundColor": "#9146ff",
                                             "borderRadius": "16px"})
        elif kind == "goal":
            piece.update(mimeType="", fillStyle={"backgroundColor": "#9146ff"},
                         toolbox={"goal": {"value": "follower-session.count", "target": 10,
                                           "label": "Follower goal: {value} / {target}"}},
                         style={"left": _px(width / 2 - 350), "top": _px(height - 120), "width": "700px",
                                "height": "56px", "backgroundColor": "rgba(0, 0, 0, 0.6)", "borderRadius": "28px",
                                "color": "#ffffff", "fontSize": "28px", "fontFamily": "Arial",
                                "fontWeight": "bold", "textShadow": "2px 2px 4px #000000"})
        elif kind == "latestTicker":
            piece.update(mimeType="text/multiline", highlightedStyle={"color": "#ffb347"},
                         text=[{"content": "{session.twitch.follower-latest.name}"}],
                         animation={"static": {"animationDuration": "10s"}},
                         toolbox={"ticker": {"kind": "follower", "count": 10, "amount": False,
                                             "between": "   \u2022   ", "look": "run"}},
                         style={"left": _px(width / 2 - 500), "top": _px(40), "width": "1000px",
                                "fontSize": "36px", "color": "#ffffff", "fontFamily": "Arial",
                                "fontWeight": "bold", "textShadow": "2px 2px 4px #000000",
                                "whiteSpace": "nowrap"})
        if kind == "video" or kind == "audio":
            piece["volume"] = 1
        if kind == "audio":
            piece["delaySeconds"] = 0
        if alert and kind != "audio":
            piece["animation"] = {"enter": {"animationName": "fade", "animationDuration": "0.5s"},
                                  "static": {"animationDuration": "5s"},
                                  "exit": {"animationName": "fade", "animationDuration": "0.5s"}}
        name = _free({"image": "Picture", "latestTicker": "Ticker"}.get(kind, KINDS[kind]), set(self.pieces(layer)))
        self.pieces(layer)[name] = piece
        if file:
            self.set_file(layer, name, file)
        return name

    def remove(self, layer: int, name: str) -> None:
        self.piece(layer, name)
        del self.pieces(layer)[name]

    def duplicate(self, layer: int, name: str) -> str:
        """A copy a little to the right and below, right above the piece; its name."""
        twin = copy.deepcopy(self.piece(layer, name))
        style = twin.get("style") or {}
        for side in ("left", "top"):
            if _number(style.get(side)) is not None:
                style[side] = _px(_number(style[side]) + 20)
        new = _free(name, set(self.pieces(layer)))
        self._put(layer, new, twin, after=name)
        return new

    def rename(self, layer: int, name: str, new: str) -> str:
        new = " ".join(str(new).split())
        if not new or new == name:
            return name
        if new in self.pieces(layer):
            raise ValueError(f"there's a piece {new!r} in this layer already")
        piece = self.piece(layer, name)
        self._put(layer, new, piece, after=name)
        del self.pieces(layer)[name]
        return new

    def restack(self, layer: int, name: str, step: int) -> None:
        """One up (+1, drawn later: over the next one) or down (-1); top / bottom with a big step."""
        pieces = self.pieces(layer)
        names = list(pieces)
        at = names.index(name)
        names.insert(max(0, min(at + step, len(names) - 1)), names.pop(at))
        items = {key: pieces[key] for key in names}
        pieces.clear()
        pieces.update(items)

    def move(self, layer: int, name: str, left: float, top: float) -> None:
        style = self.piece(layer, name).setdefault("style", {})
        style["left"], style["top"] = _px(left), _px(top)

    def resize(self, layer: int, name: str, width: float, font_size: float | None = None,
               height: float | None = None) -> None:
        """Its width; a text also its letters (dragging a text's corner makes all of it bigger), a shape or a
        goal bar its height."""
        style = self.piece(layer, name).setdefault("style", {})
        style["width"] = _px(max(width, 4))
        if font_size is not None:
            style["fontSize"] = _px(max(font_size, 1))
        if height is not None:
            style["height"] = _px(max(height, 4))

    def set_style(self, layer: int, name: str, **style: Any) -> None:
        """CSS of the piece (fontSize="40px", color=...); None or "" takes it away."""
        own = self.piece(layer, name).setdefault("style", {})
        for key, value in style.items():
            if value is None or value == "":
                own.pop(key, None)
            else:
                own[key] = value

    def set_fill(self, layer: int, name: str, color: str) -> None:
        """The colour of a goal bar's part that is reached."""
        self.piece(layer, name).setdefault("fillStyle", {})["backgroundColor"] = color

    def goal(self, layer: int, name: str) -> dict[str, Any]:
        """A goal bar's {value: what it counts (GOALS), target, label: its words, {value} {target} {percent}
        filled in}."""
        found = (self.piece(layer, name).get("toolbox") or {}).get("goal") or {}
        return {"value": found.get("value") if found.get("value") in GOALS else "follower-session.count",
                "target": _plain_number(found.get("target") or 10),
                "label": str(found.get("label") if found.get("label") is not None else "{value} / {target}")}

    def set_goal(self, layer: int, name: str, **changes: Any) -> None:
        now = {**self.goal(layer, name), **changes}
        if now["value"] not in GOALS:
            raise ValueError(f"a goal bar can't count {now['value']!r}")
        now["target"] = _plain_number(max(float(now["target"] or 1), 1))
        self.piece(layer, name).setdefault("toolbox", {})["goal"] = now

    def ticker(self, layer: int, name: str) -> dict[str, Any] | None:
        """A ticker of the editor's: {kind (TICKERS), count, amount: theirs after the name, between, look
        (TICKER_LOOKS), seconds: one round}; None for a StreamElements one (its text says what it shows)."""
        piece = self.piece(layer, name)
        found = (piece.get("toolbox") or {}).get("ticker")
        if not isinstance(found, dict):
            return None
        return {"kind": found.get("kind") if found.get("kind") in TICKERS else "follower",
                "count": max(1, min(int(found.get("count") or 10), 25)), "amount": bool(found.get("amount")),
                "between": str(found.get("between") if found.get("between") is not None else " "),
                "look": found.get("look") if found.get("look") in TICKER_LOOKS else "run",
                "seconds": _number(((piece.get("animation") or {}).get("static") or {}).get("animationDuration"))
                or 10}

    def set_ticker(self, layer: int, name: str, **changes: Any) -> None:
        now = {**(self.ticker(layer, name) or {}), **changes}
        if now.get("kind") not in TICKERS or now.get("look") not in TICKER_LOOKS:
            raise ValueError("not a ticker")
        piece = self.piece(layer, name)
        seconds = max(float(now.pop("seconds", 10) or 10), 1)
        now["count"] = max(1, min(int(now["count"]), 25))
        piece.setdefault("toolbox", {})["ticker"] = now
        piece.setdefault("animation", {}).setdefault("static", {})["animationDuration"] = _seconds(seconds)
        piece["text"] = [{"content": f"{{session.twitch.{now['kind']}-latest.name}}"}]  # what it names
        piece.setdefault("style", {})["whiteSpace"] = "pre" if now["look"] == "lines" else "nowrap"

    def set_highlight(self, layer: int, name: str, color: str) -> None:
        """The colour of the filled-in words (the latest follower's name in "Latest follower: …")."""
        self.piece(layer, name).setdefault("highlightedStyle", {})["color"] = color

    def text(self, layer: int, name: str) -> str:
        return "\n".join(str(line.get("content") or "") for line in self.piece(layer, name).get("text") or [])

    def set_text(self, layer: int, name: str, text: str) -> None:
        piece = self.piece(layer, name)
        piece["text"] = [{**(piece.get("text") or [{}])[0], "content": str(text)}]

    def file(self, layer: int, name: str) -> str:
        media = [m for m in self.piece(layer, name).get("media") or [] if m.get("role") not in ("font-face",)]
        return str(media[0].get("href") or "") if media else ""

    def set_file(self, layer: int, name: str, file: str) -> None:
        """The picture, video or sound file (a file of the widget's media folder, or an address)."""
        piece = self.piece(layer, name)
        ending = "." + file.rsplit(".", 1)[-1].casefold() if "." in file else ""
        kind = piece.get("type")
        mime = ENDINGS.get(ending, f"{kind}/*")
        if not mime.startswith(f"{kind}/"):
            raise ValueError(f"{file} is no {KINDS.get(kind, kind).casefold()}")
        fonts = [m for m in piece.get("media") or [] if m.get("role") == "font-face"]
        piece["media"] = [{"href": file, "mimeType": mime}, *fonts]

    def set_volume(self, layer: int, name: str, volume: float) -> None:
        self.piece(layer, name)["volume"] = max(0.0, min(float(volume), 1.0))

    def set_delay(self, layer: int, name: str, seconds: float) -> None:
        self.piece(layer, name)["delaySeconds"] = max(float(seconds), 0.0)

    def animation(self, layer: int, name: str) -> dict[str, Any]:
        """How a piece of an alert comes in, how long it stays, how it goes out: {in, in_seconds, delay, stays,
        out, out_seconds}. A stay of 0: as long as its video runs (or the alert's other pieces)."""
        found = self.piece(layer, name).get("animation") or {}
        enter, hold, exit_ = (found.get(phase) or {} for phase in ("enter", "static", "exit"))
        return {"in": _ours(enter.get("animationName"), ANIMATIONS_IN),
                "in_seconds": _number(enter.get("animationDuration")) or 0,
                "delay": _number(enter.get("animationDelay")) or 0,
                "stays": _number(hold.get("animationDuration")) or 0,
                "out": _ours(exit_.get("animationName"), ANIMATIONS_OUT),
                "out_seconds": _number(exit_.get("animationDuration")) or 0}

    def set_animation(self, layer: int, name: str, **changes: Any) -> None:
        """Changes some of what animation() gives (in, in_seconds, delay, stays, out, out_seconds)."""
        now = {**self.animation(layer, name), **changes}
        found = self.piece(layer, name).setdefault("animation", {})
        enter, hold, exit_ = (found.setdefault(phase, {}) for phase in ("enter", "static", "exit"))
        for phase, key, value, names in ((enter, "in", now["in"], ANIMATIONS_IN), (exit_, "out", now["out"], ANIMATIONS_OUT)):
            if key in changes:
                phase.pop("opacity", None)  # StreamElements' own fade: ours is played from the name
                if value:
                    phase["animationName"] = value if value in names else "fade"
                else:
                    phase.pop("animationName", None)
        enter["animationDuration"] = _seconds(now["in_seconds"])
        enter["animationDelay"] = _seconds(now["delay"])
        hold["animationDuration"] = _seconds(now["stays"])
        exit_["animationDuration"] = _seconds(now["out_seconds"])

    def reaction(self, layer: int, name: str) -> dict[str, Any]:
        """What a piece that is always there does on an event: {events, animation, seconds}; no events: nothing."""
        found = (self.piece(layer, name).get("toolbox") or {}).get("react") or {}
        return {"events": [e for e in found.get("events") or [] if e in EVENTS],
                "animation": found.get("animation") if found.get("animation") in REACTIONS else "pop",
                "seconds": float(found.get("seconds") or 0.8)}

    def set_reaction(self, layer: int, name: str, events: list[str], animation: str = "pop",
                     seconds: float = 0.8) -> None:
        piece = self.piece(layer, name)
        own = piece.setdefault("toolbox", {})
        events = [e for e in events if e in EVENTS]
        if not events:
            own.pop("react", None)
        else:
            own["react"] = {"events": events, "animation": animation if animation in REACTIONS else "pop",
                            "seconds": max(0.1, min(float(seconds), 10.0))}
        if not own:
            piece.pop("toolbox", None)

    def events(self) -> set[str]:
        """The events it needs (follower, subscriber, ...): an alert's, a piece's reaction, and the kinds its
        texts, goal bars and tickers show (a widget gets the new session data only after its own events)."""
        found = set()
        for number, state in enumerate(self.config["configStates"]):
            if not self._on(state):
                continue
            if state.get("categoryId") in EVENTS:
                found.add(state["categoryId"])
            for name, piece in self.pieces(number).items():
                found.update(self.reaction(number, name)["events"])
                found.update(KIND_OF.findall(self.text(number, name)))
                if piece.get("type") == "goal":
                    found.add(self.goal(number, name)["value"].split("-")[0])
                ticker = self.ticker(number, name) if piece.get("type") == "latestTicker" else None
                if ticker:
                    found.add(ticker["kind"])
        return found & set(EVENTS)

    def files(self) -> set[str]:
        """The files of the media folder its pieces use (not addresses)."""
        used = set()
        for state in self.config["configStates"]:
            for piece in ((state.get("settings") or {}).get("compositeFields") or {}).values():
                for media in piece.get("media") or []:
                    href = str(media.get("href") or "")
                    if href and "/" not in href:
                        used.add(href)
        return used

    def _state(self, layer: int) -> dict[str, Any]:
        states = self.config["configStates"]
        if not 0 <= layer < len(states):
            raise KeyError(f"no layer {layer}")
        return states[layer]

    def _put(self, layer: int, name: str, piece: dict[str, Any], after: str) -> None:
        pieces = self.pieces(layer)
        items = {}
        for key, value in pieces.items():
            items[key] = value
            if key == after:
                items[name] = piece
        pieces.clear()
        pieces.update(items)


def _free(wanted: str, taken: set[str]) -> str:
    """The name, or with the next free number ("Picture 2")."""
    found = NUMBERED.fullmatch(wanted)
    base, number = (found.group(1), int(found.group(2))) if found else (wanted, 1)
    name = wanted if wanted not in taken else ""
    while not name or name in taken:
        number += 1
        name = f"{base} {number}"
    return name


def _is(part: Any, operator: str, left: dict[str, str]) -> bool:
    """{">=": [{"var": "event.data.amount"}, 100]} is (">=", amount)."""
    return (isinstance(part, dict) and list(part) == [operator] and isinstance(part[operator], list)
            and len(part[operator]) == 2 and part[operator][0] == left
            and isinstance(part[operator][1], (int, float)))


def _plain_number(value: Any) -> int | float:
    number = float(value)
    return int(number) if number.is_integer() else number


def _layer(event: str) -> dict[str, Any]:
    if event == "static":
        return {"referenceId": "static", "categoryId": None, "displayName": "Always there",
                "triggers": [{"systemCondition": {}, "userCondition": {}}], "settings": {"compositeFields": {}}}
    rule = [{"==": [{"var": "event.topic"}, "event"]}, {"==": [{"var": "event.type"}, EVENTS[event]]}]
    if event == "subscriber":  # a gift bomb has its own alert (communityGiftPurchase), as in StreamElements
        rule.append({"!=": [{"var": "event.data.gifted"}, True]})
    return {"referenceId": str(uuid.uuid4()), "categoryId": event, "displayName": "Default",
            "triggers": [{"systemCondition": {"and": rule}, "userCondition": {}}],
            "settings": {"compositeFields": {}}}


def _has_own_condition(state: dict[str, Any]) -> bool:
    return any(trigger.get("userCondition") for trigger in state.get("triggers") or [])


def _ours(name: Any, names: dict[str, str]) -> str:
    """An animation's name as the editor's list has it; StreamElements' own (fade-in, ...) element.js plays as
    a fade."""
    return "" if not name else str(name) if name in names else "fade"


def _px(value: float) -> str:
    return f"{_plain(round(float(value), 2))}px"


def _seconds(value: Any) -> str:
    return f"{_plain(max(float(value or 0), 0))}s"
