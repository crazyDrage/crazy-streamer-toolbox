import re
from dataclasses import dataclass
from typing import Any

# an input's type → (its name in the Inputs tab, the box's fields, the trigger its flow starts on ("" = Manual),
# the listener StreamElements' code checks for it). The fields are the trigger's own, so the flow wires them 1:1.
KINDS: dict[str, tuple[str, tuple[str, ...], str, str]] = {
    "chat": ("Chat message", ("user", "message", "platform", "color", "role", "user_id", "message_id", "emotes"),
             "chat", "message"),
    "chat_deleted": ("Chat message deleted", ("message_id", "user_id"), "twitch.chat_deleted", "delete-message"),
    "follow": ("Follow", ("user", "platform"), "follow", "follower-latest"),
    "sub": ("Sub", ("user", "tier", "gift", "platform"), "sub", "subscriber-latest"),
    "resub": ("Resub", ("user", "tier", "months", "message", "platform"), "resub", "subscriber-latest"),
    "gift": ("Gift subs", ("user", "amount", "tier", "platform"), "gift", "subscriber-latest"),
    "cheer": ("Cheer", ("user", "bits", "message", "platform"), "cheer", "cheer-latest"),
    "raid": ("Raid", ("user", "viewers", "platform"), "raid", "raid-latest"),
    "tip": ("Tip", ("user", "amount", "currency", "message"), "tip", "tip-latest"),
    "custom": ("Custom (fields you name)", (), "", ""),
}
NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")


@dataclass(frozen=True)
class WidgetInput:
    """Something a widget got from a flow before round 78 (inputs.json; EventConversion makes them event types
    once; his round 74: "For every widget we need to set inputs, have input types"): a name (its box in flows: "<widget> · <name>"), a type (KINDS: a chat message, a follow, ...,
    or custom with fields he names) and the listener the widget's code receives it as (onEventReceived's
    obj.detail.listener; empty = the type's StreamElements one, a custom input's own name). Nothing reaches a
    widget by itself any more (his answer 1 a): a flow sends it, with this input's box."""

    name: str
    kind: str = "chat"
    listener: str = ""
    fields: str = ""  # a custom input's fields: "title, amount"

    @property
    def heard_as(self) -> str:
        return self.listener.strip() or KINDS[self.kind][3] or self.name

    @property
    def field_names(self) -> tuple[str, ...]:
        if self.kind != "custom":
            return KINDS[self.kind][1]
        return tuple(dict.fromkeys(name for name in re.split(r"[,\s]+", self.fields) if NAME.fullmatch(name)))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WidgetInput":
        kind = data.get("kind")
        return cls(str(data.get("name") or "input"), kind if kind in KINDS else "custom",
                   str(data.get("listener") or ""), str(data.get("fields") or ""))

    def to_dict(self) -> dict[str, Any]:
        data = {"name": self.name, "kind": self.kind}
        if self.listener:
            data["listener"] = self.listener
        if self.fields:
            data["fields"] = self.fields
        return data


def check_input_name(name: str) -> str:
    name = str(name).strip()
    if not NAME.fullmatch(name):
        raise ValueError("an input's name is letters, digits, _ and - (no spaces), e.g. chat or follower-latest")
    return name

