"""The alerts the toolbox starts with (his round 65), each on the event type of its name (round 78), and the
words a new alert on one of those events starts with.

event (a common event: every platform's follow is `follow`) → its name, its text, its trigger's match and its
inputs: (name, kind, example, is the amount, the event field its flow wires into it). An input is named like
the event type's value (Overlay → Events: cheer has bits), so the alert's inputs are that event's values."""
from typing import Any

from streamer_toolbox.core.alerts.alert_input import AlertInput

EXAMPLE_MESSAGE = "(their message shows here)"  # says what it is: nobody takes it for words of the alert
FOLDER = "Alerts"  # where the flows that start alerts are listed
USER = ("user", "text", "TestViewer", False, "user")
MESSAGE = ("message", "text", EXAMPLE_MESSAGE, False, "message")
TIER = ("tier", "number", "1", False, "tier")

STARTERS: dict[str, tuple[str, str, dict[str, str], tuple[tuple[str, str, str, bool, str], ...]]] = {
    "follow": ("Follow", "{user} just followed!", {}, (USER,)),
    # a gifted sub has no alert of its own: the gifter's Gift subs alert covers them (five gifts are one alert)
    "sub": ("Sub", "{user} just subscribed!", {"gift": "false"}, (USER, TIER)),
    "resub": ("Resub", "{user} subscribed for {months} months!", {},
              (USER, ("months", "number", "7", True, "months"), TIER, MESSAGE)),
    "gift": ("Gift subs", "{user} gifted {amount} subs!", {}, (USER, ("amount", "number", "5", True, "amount"), TIER)),
    "cheer": ("Cheer", "{user} cheered {amount} bits!", {}, (USER, ("bits", "number", "100", True, "bits"), MESSAGE)),
    "raid": ("Raid", "{user} is raiding with {amount} viewers!", {}, (USER, ("viewers", "number", "42", True, "viewers"))),
    "tip": ("Tip", "{user} tipped {amount} {currency}!", {},
            (USER, ("amount", "number", "5", True, "amount"), ("currency", "text", "EUR", False, "currency"), MESSAGE)),
    "redeem": ("Redeem", "{user} redeemed {reward}!", {},
               (USER, ("reward", "text", "Lizard", False, "reward"), ("input", "text", "", False, "input"))),
}
# the alerts every toolbox has from the start (Redeem is only offered for new ones)
FIRST = ("follow", "sub", "resub", "gift", "cheer", "raid", "tip")
# the fixed alerts before round 65, by the event they were tied to → their starter
OLD_EVENTS = {"twitch.follow": "follow", "twitch.sub": "sub", "twitch.resub": "resub", "twitch.gift": "gift",
              "twitch.cheer": "cheer", "twitch.raid": "raid", "tip": "tip"}
# what those events had besides the inputs above, as {name} in an alert's words: (kind, example, event field)
OLD_FIELDS: dict[str, dict[str, tuple[str, str, str]]] = {
    "resub": {"amount": ("number", "7", "months")},
    "cheer": {"bits": ("number", "100", "bits")},
    "raid": {"viewers": ("number", "42", "viewers")},
    "tip": {"platform": ("text", "test", "platform")},
}


def inputs(event: str) -> tuple[AlertInput, ...]:
    return tuple(AlertInput(name, kind, example, amount) for name, kind, example, amount, _ in STARTERS[event][3])


def wiring(event: str) -> dict[str, str]:
    """input → the event field its flow wires into it."""
    return {name: field for name, _, _, _, field in STARTERS[event][3]}


def examples(event: str) -> dict[str, Any]:
    return {name: example for name, _, example, _, _ in STARTERS[event][3]}
