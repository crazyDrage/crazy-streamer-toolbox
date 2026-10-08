from dataclasses import dataclass, replace
from typing import Any

from streamer_toolbox.core.alerts.alert import Alert
from streamer_toolbox.core.alerts.alert_look import AlertLook
from streamer_toolbox.core.alerts.alert_part import PARTS, AlertPart
from streamer_toolbox.core.alerts.alert_variation import AlertVariation

# what the example viewer wrote: it says what it is, so nobody takes it for words of the alert itself
EXAMPLE_MESSAGE = "(their message shows here)"
# event → (its name in the Alerts tool, the text it starts with, the event field that is its amount ("" = none),
#          example data for the Test button)
ALERT_EVENTS: dict[str, tuple[str, str, str, dict[str, Any]]] = {
    "twitch.follow": ("Follow", "{user} just followed!", "", {"user": "TestViewer"}),
    "twitch.sub": ("Sub", "{user} just subscribed!", "", {"user": "TestViewer", "tier": 1, "gift": False}),
    "twitch.resub": ("Resub", "{user} subscribed for {months} months!", "months",
                     {"user": "TestViewer", "tier": 1, "months": 7, "message": EXAMPLE_MESSAGE}),
    "twitch.gift": ("Gift subs", "{user} gifted {amount} subs!", "amount",
                    {"user": "TestViewer", "amount": 5, "tier": 1}),
    "twitch.cheer": ("Cheer", "{user} cheered {amount} bits!", "bits",
                     {"user": "TestViewer", "bits": 100, "message": EXAMPLE_MESSAGE}),
    "twitch.raid": ("Raid", "{user} is raiding with {amount} viewers!", "viewers",
                    {"user": "TestViewer", "viewers": 42}),
    "tip": ("Tip", "{user} tipped {amount} {currency}!", "amount",
            {"user": "TestViewer", "amount": 5, "currency": "EUR", "message": EXAMPLE_MESSAGE, "platform": "test"}),
}
SOMEONE = "Someone"  # an anonymous gifter / cheerer has no name


@dataclass(frozen=True)
class AlertRule:
    """What the Alerts tool shows for one kind of event: on / off, the text ({user}, {amount}, and every field
    the event has: {months}, {tier}, {message}, ...), picture, sound, how long, how loud, and the smallest
    amount that still gets an alert (bits, raid viewers, gifted subs, months), its look (AlertLook),
    variations (a different text / picture / sound from a bigger amount on), and `parts`: the list of the
    pieces of its words (AlertPart: text line, name, amount, their message), in the order they stack; pieces
    are added to it and taken out of it. A new alert starts with default_parts: the text line, and their
    message if the event has one."""

    event: str
    on: bool = False
    text: str = ""
    image: str = ""
    sound: str = ""
    seconds: float = 5.0
    volume: float = 1.0
    minimum: int = 0
    look: AlertLook = AlertLook()
    variations: tuple[AlertVariation, ...] = ()  # bigger alerts from an amount on, see variation_for
    parts: tuple[AlertPart, ...] = ()

    @classmethod
    def default(cls, event: str) -> "AlertRule":
        return cls(event, text=ALERT_EVENTS[event][1], parts=default_parts(event))

    @classmethod
    def from_dict(cls, event: str, data: dict[str, Any]) -> "AlertRule":
        start = cls.default(event)
        return cls(event, bool(data.get("on", False)), str(data.get("text", start.text)),
                   str(data.get("image", "")), str(data.get("sound", "")), float(data.get("seconds", 5.0)),
                   float(data.get("volume", 1.0)), int(data.get("minimum", 0)),
                   AlertLook.from_dict(data.get("look")),
                   tuple(AlertVariation.from_dict(v) for v in data.get("variations", [])), _parts(event, data))

    def to_dict(self) -> dict[str, Any]:
        return {"on": self.on, "text": self.text, "image": self.image, "sound": self.sound,
                "seconds": self.seconds, "volume": self.volume, "minimum": self.minimum,
                "look": self.look.to_dict(), "variations": [v.to_dict() for v in self.variations],
                "pieces": [p.to_dict() for p in self.parts]}

    def add_part(self, part: AlertPart) -> "AlertRule":
        """This alert with one more piece, last in its list."""
        return replace(self, parts=(*self.parts, part))

    def with_part(self, index: int, part: AlertPart) -> "AlertRule":
        """This alert with the piece at that place of its list set up like this."""
        return replace(self, parts=(*self.parts[:index], part, *self.parts[index + 1:]))

    def without_part(self, index: int) -> "AlertRule":
        """This alert without the piece at that place of its list."""
        return replace(self, parts=(*self.parts[:index], *self.parts[index + 1:]))

    def part_up(self, index: int) -> "AlertRule":
        """This alert with that piece one place earlier in its list (the first one stays)."""
        if index < 1:
            return self
        parts = list(self.parts)
        parts[index - 1], parts[index] = parts[index], parts[index - 1]
        return replace(self, parts=tuple(parts))

    @property
    def title(self) -> str:
        return ALERT_EVENTS[self.event][0]

    @property
    def has_amount(self) -> bool:
        return bool(ALERT_EVENTS[self.event][2])

    @property
    def has_message(self) -> bool:
        return "message" in ALERT_EVENTS[self.event][3]

    def wants(self, data: dict[str, Any]) -> bool:
        """On, the amount is big enough, and it isn't a gifted sub arriving (the gifter's alert covers those:
        five gifted subs are one Gift subs alert, not five Sub alerts on top)."""
        if not self.on or (self.event == "twitch.sub" and data.get("gift")):
            return False
        return not self.has_amount or _number(data.get(ALERT_EVENTS[self.event][2])) >= self.minimum

    def variation_for(self, amount: Any) -> AlertVariation | None:
        """The variation with the highest "from" that the amount reaches, None if it reaches none."""
        reached = [v for v in self.variations if _number(amount) >= v.minimum]
        return max(reached, key=lambda v: v.minimum) if reached else None

    def alert_for(self, data: dict[str, Any]) -> Alert:
        user = str(data.get("user") or SOMEONE)
        amount = data.get(ALERT_EVENTS[self.event][2], "") if self.has_amount else ""
        bigger = self.variation_for(amount) if self.has_amount else None
        values = {**{k: v for k, v in data.items() if isinstance(v, (str, int, float))},
                  "user": user, "amount": amount}
        values.setdefault("message", "")
        line = (bigger.text if bigger else "") or self.text
        words: dict[str, str] = {}
        views = []
        said_in_stack = any("{message}" in (p.text or line) for p in self.parts
                            if p.kind == "text" and not p.on_picture)
        for index, piece in enumerate(self.parts):
            said = _fill(piece.template or line, values)
            if piece.kind == "message" and not piece.on_picture and said_in_stack:
                said = ""  # a text line says it already: not twice in the stack
            if said:
                words.setdefault(piece.kind, said)
                views.append(piece.view(index, said))
        return Alert(words.get("text", ""), (bigger.image if bigger else "") or self.image,
                     (bigger.sound if bigger else "") or self.sound, self.seconds, self.volume,
                     (user, str(amount)), words.get("message", ""), self.look, tuple(views))


def _fill(template: str, values: dict[str, Any]) -> str:
    for key, value in values.items():
        template = template.replace("{" + key + "}", str(value))
    return template.strip()


def default_parts(event: str) -> tuple[AlertPart, ...]:
    """The pieces an alert starts with: the text line, and their message if the event has one."""
    with_message = "message" in ALERT_EVENTS[event][3]
    return (AlertPart("text"), AlertPart("message")) if with_message else (AlertPart("text"),)


def _parts(event: str, data: dict[str, Any]) -> tuple[AlertPart, ...]:
    """The pieces a file holds: its "pieces" list, as it is. Older files had "parts": one entry per kind with
    a "shown" switch, and a kind that wasn't in it had its default (the text line and the message shown); the
    shown ones become the list. Files from before there were pieces: "with_message": false = no message piece;
    a look with text_place "over" = the text line sits on the picture at its text_x / text_y."""
    if "pieces" in data:
        return tuple(AlertPart.from_dict(p) for p in data["pieces"]
                     if isinstance(p, dict) and p.get("kind") in PARTS)
    old = {p["key"]: p for p in data.get("parts", []) if isinstance(p, dict) and p.get("key") in PARTS}
    look = data.get("look") or {}
    if "message" not in old and data.get("with_message") is False:
        old["message"] = {"shown": False}
    if "text" not in old and look.get("text_place") == "over":
        old["text"] = {"on_picture": True, "x": look.get("text_x", 50), "y": look.get("text_y", 50)}
    usual = {part.kind for part in default_parts(event)}
    fits = {"amount": bool(ALERT_EVENTS[event][2]), "message": "message" in ALERT_EVENTS[event][3]}
    return tuple(AlertPart.from_dict({**old.get(kind, {}), "kind": kind}) for kind in PARTS
                 if old.get(kind, {}).get("shown", kind in usual) and fits.get(kind, True))


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
