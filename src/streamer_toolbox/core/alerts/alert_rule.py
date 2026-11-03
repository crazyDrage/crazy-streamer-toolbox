from dataclasses import dataclass, replace
from typing import Any

from streamer_toolbox.core.alerts import alert_starters
from streamer_toolbox.core.alerts.alert import Alert
from streamer_toolbox.core.alerts.alert_input import AlertInput
from streamer_toolbox.core.alerts.alert_look import AlertLook
from streamer_toolbox.core.alerts.alert_part import PARTS, AlertPart
from streamer_toolbox.core.alerts.alert_variation import AlertVariation

SOMEONE = "Someone"  # an anonymous gifter / cheerer has no name


@dataclass(frozen=True)
class AlertRule:
    """One alert of the Alerts tool (his round 65: his own list, not a fixed one). `id` stays when he renames it
    ("Only to: alert <id>" on a Send box), `name` is what he calls it, `inputs` what it gets each time it
    plays (AlertInput: user, amount, message, a picture, ...; its words use them as {user}). It plays when its
    event is sent (the flows in the folder Events).

    On / off, the text, picture, sound, how long, how loud, the smallest amount that still gets an alert, its
    look (AlertLook), variations (a different text / picture / sound from a bigger amount on), and `parts`: the
    pieces of its words (AlertPart: text line, name, amount, their message), in the order they stack.

    `event`: the event type it plays on (Overlay → Events, his round 78). Its inputs are that event's values
    (EventUsers keeps them in step); what stays the alert's own is each input's example and which is the amount."""

    id: str
    name: str = ""
    inputs: tuple[AlertInput, ...] = ()
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
    event: str = ""

    @classmethod
    def starter(cls, event: str, id_: str = "") -> "AlertRule":
        """One of the alerts the toolbox starts with ("follow", "resub", ...: alert_starters), off."""
        name, text, _, _ = alert_starters.STARTERS[event]
        inputs = alert_starters.inputs(event)
        return cls(id_ or event, name, inputs, text=text, parts=default_parts(inputs), event=event)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AlertRule":
        inputs = tuple(AlertInput.from_dict(i) for i in data.get("inputs", []) if isinstance(i, dict))
        return cls(str(data["id"]), str(data.get("name", "")), inputs, bool(data.get("on", False)),
                   str(data.get("text", "")), str(data.get("image", "")), str(data.get("sound", "")),
                   float(data.get("seconds", 5.0)), float(data.get("volume", 1.0)), int(data.get("minimum", 0)),
                   AlertLook.from_dict(data.get("look")),
                   tuple(AlertVariation.from_dict(v) for v in data.get("variations", [])), _parts(inputs, data),
                   str(data.get("event", "")))

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "inputs": [i.to_dict() for i in self.inputs], "on": self.on,
                "text": self.text, "image": self.image, "sound": self.sound, "seconds": self.seconds,
                "volume": self.volume, "minimum": self.minimum, "look": self.look.to_dict(),
                "variations": [v.to_dict() for v in self.variations], "pieces": [p.to_dict() for p in self.parts],
                "event": self.event}

    @property
    def title(self) -> str:
        return self.name or self.id

    @property
    def amount_input(self) -> str:
        """The name of the input that is its amount, "" if it has none."""
        return next((i.name for i in self.inputs if i.amount), "")

    @property
    def has_amount(self) -> bool:
        return bool(self.amount_input)

    @property
    def has_message(self) -> bool:
        return any(i.name == "message" for i in self.inputs)

    def input(self, name: str) -> AlertInput | None:
        return next((i for i in self.inputs if i.name == name), None)

    def examples(self) -> dict[str, Any]:
        """Its inputs' examples: what Test and the preview show."""
        return {i.name: i.value(i.example) for i in self.inputs}

    # ---- its inputs ----

    def with_inputs(self, inputs: tuple[AlertInput, ...]) -> "AlertRule":
        """With these inputs; at most one is the amount (the last one ticked wins)."""
        ticked = [i.name for i in inputs if i.amount]
        keep = ticked[-1] if ticked else ""
        return replace(self, inputs=tuple(replace(i, amount=i.name == keep) for i in inputs))

    def renamed_input(self, old: str, new: str) -> "AlertRule":
        """The input called old is called new, and {old} in its words, pieces and bigger alerts says {new}."""
        def swap(text: str) -> str:
            return text.replace("{" + old + "}", "{" + new + "}")
        return replace(self, inputs=tuple(replace(i, name=new) if i.name == old else i for i in self.inputs),
                       text=swap(self.text), image=swap(self.image), sound=swap(self.sound),
                       parts=tuple(replace(p, text=swap(p.text)) for p in self.parts),
                       variations=tuple(replace(v, text=swap(v.text)) for v in self.variations))

    # ---- the pieces of its words ----

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

    # ---- playing it ----

    def wants(self, values: dict[str, Any]) -> bool:
        """On, and the amount (if it has one) is big enough."""
        return self.on and (not self.has_amount or _number(values.get(self.amount_input)) >= self.minimum)

    def variation_for(self, amount: Any) -> AlertVariation | None:
        """The variation with the highest "from" that the amount reaches, None if it reaches none."""
        reached = [v for v in self.variations if _number(amount) >= v.minimum]
        return max(reached, key=lambda v: v.minimum) if reached else None

    def alert_for(self, given: dict[str, Any]) -> Alert:
        """The alert with these values for its inputs ({user}, {amount}, ...; anything else given can be said
        too). An empty user is "Someone". {amount} is its amount input's value, whatever that is called."""
        values = {k: v for k, v in given.items() if isinstance(v, (str, int, float))}
        for spec in self.inputs:
            values[spec.name] = spec.value(given.get(spec.name))
        if "user" in values and not str(values["user"]).strip():
            values["user"] = SOMEONE
        amount = values.get(self.amount_input, "") if self.has_amount else ""
        values.setdefault("amount", amount)
        values.setdefault("message", "")
        bigger = self.variation_for(amount) if self.has_amount else None
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
        image = _fill((bigger.image if bigger else "") or self.image, values) or self._given("picture", values)
        sound = _fill((bigger.sound if bigger else "") or self.sound, values) or self._given("sound", values)
        return Alert(words.get("text", ""), image, sound, self.seconds, self.volume,
                     (str(values.get("user", "")), str(amount)), words.get("message", ""), self.look, tuple(views))

    def _given(self, kind: str, values: dict[str, Any]) -> str:
        """The file a picture / sound input got, when the alert has none of its own."""
        return next((str(values[i.name]).strip().strip('"') for i in self.inputs
                     if i.kind == kind and str(values.get(i.name) or "").strip()), "")


def _fill(template: str, values: dict[str, Any]) -> str:
    for key, value in values.items():
        template = template.replace("{" + key + "}", str(value))
    return template.strip()


def default_parts(inputs: tuple[AlertInput, ...]) -> tuple[AlertPart, ...]:
    """The pieces an alert starts with: the text line, and their message if it has a message input."""
    with_message = any(i.name == "message" for i in inputs)
    return (AlertPart("text"), AlertPart("message")) if with_message else (AlertPart("text"),)


def _parts(inputs: tuple[AlertInput, ...], data: dict[str, Any]) -> tuple[AlertPart, ...]:
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
    usual = {part.kind for part in default_parts(inputs)}
    fits = {"amount": any(i.amount for i in inputs), "message": any(i.name == "message" for i in inputs)}
    return tuple(AlertPart.from_dict({**old.get(kind, {}), "kind": kind}) for kind in PARTS
                 if old.get(kind, {}).get("shown", kind in usual) and fits.get(kind, True))


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
