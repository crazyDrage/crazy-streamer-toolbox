import re
from typing import Any

from streamer_toolbox.core.event_types.event_type import EventType

# what a text that is always there can show: (its name in the editor, its code in the Element's text)
ALWAYS = (
    ("Latest follower", "{session.twitch.follower-latest.name}"),
    ("Latest subscriber", "{session.twitch.subscriber-latest.name}"),
    ("Latest sub's months", "{session.twitch.subscriber-latest.amount}"),
    ("Latest cheerer", "{session.twitch.cheer-latest.name}"),
    ("Latest cheer's bits", "{session.twitch.cheer-latest.amount}"),
    ("Latest raider", "{session.twitch.raid-latest.name}"),
    ("Latest raid's viewers", "{session.twitch.raid-latest.amount}"),
    ("Latest tipper", "{session.twitch.tip-latest.name}"),
    ("Latest tip", "{session.twitch.tip-latest.amount}"),
    ("Followers this stream", "{session.twitch.follower-session.count}"),
    ("Subs this stream", "{session.twitch.subscriber-session.count}"),
    ("Bits this stream", "{session.twitch.cheer-session.amount}"),
    ("Raids this stream", "{session.twitch.raid-session.count}"),
    ("Tips this stream", "{session.twitch.tip-session.amount}"),
    ("Followers this month", "{session.twitch.follower-month.count}"),
    ("Subs this month", "{session.twitch.subscriber-month.count}"),
    ("Bits this month", "{session.twitch.cheer-month.amount}"),
    ("Followers in all", "{session.twitch.follower-total.count}"),
    ("Subs in all", "{session.twitch.subscriber-total.count}"),
    ("Sub points", "{session.twitch.subscriber-points.amount}"),
    ("Top cheerer this stream", "{session.twitch.cheer-session-top-donator.name}"),
    ("Top cheerer's bits this stream", "{session.twitch.cheer-session-top-donator.amount}"),
    ("Top tipper this stream", "{session.twitch.tip-session-top-donator.name}"),
)
# what a text of an alert can show besides: the event's own values
ALERT = (
    ("Their name", "{event.data.username}"),
    ("Amount (months, bits, viewers)", "{event.data.amount}"),
    ("Their message", "{event.data.message}"),
    ("Currency sign", "{event.data.currency}"),
)
# the stage shows these where a value is still empty (nobody followed yet)
SAMPLE_NAME = "TestViewer"
SAMPLE_EVENT = {"username": SAMPLE_NAME, "displayName": SAMPLE_NAME, "amount": 3, "message": "Hello there!",
                "currency": "$"}
SAMPLE_MESSAGES = ("Hello there!", "What a play!", "Good luck today")
# an event list's event (StreamElements' word, what a widget hears) → the event types (Overlay → Events) it
# comes as. An entry's values are theirs, 1:1 by their names (his 11-13: "the values should be 1to1 the same
# name as the event values"); a widget's code reads them under their "also known as" names too
LIST_TYPES = {"follower": ("follow",), "subscriber": ("sub", "resub", "gift"),
              "communityGiftPurchase": ("community_gift",), "cheer": ("cheer",), "raid": ("raid",),
              "tip": ("tip",), "message": ("chat",)}
# the first event lists' codes ({event.data.username}) → the value's name; amount was each event's own
OLD_KEYS = {"username": "user", "service": "platform", "login": "user_login", "time": ""}
OLD_AMOUNTS = {"subscriber": "months", "cheer": "bits", "raid": "viewers"}
OLD_CODE = re.compile(r"\{event\.data\.([\w-]+)\}")
# an example of each value the editor's preview fills in where the event type's default is empty
SAMPLE_VALUES = {"user": SAMPLE_NAME, "message": "Hello there!", "platform": "twitch", "currency": "$",
                 "role": "viewer"}
CODE = re.compile(r"\{([^{}]+)\}")
WORD = re.compile(r"\[([^\[\]]+)\]")


class DesignValues:
    """The values a text of the widget editor can show (latest follower, their name, ...) by name: he picks them
    from a list and reads them as [Latest follower] in the text box, element.js gets its {…} codes. A code
    without a name here (from an imported Element) stays as it is. fill() gives a text as the editor's canvas
    shows it: with what the toolbox knows now (the session data), an example where that is still empty."""

    @staticmethod
    def names(alert: bool) -> list[tuple[str, str]]:
        return [*(ALERT if alert else ()), *ALWAYS]

    @staticmethod
    def list_values(event: str, kinds: list[EventType]) -> list[dict[str, Any]]:
        """What an event list's entry of that event can show: the values of its event types (LIST_TYPES; kinds:
        the event types there are now), each once, in their order: {"name", "aka": its other names, "default"}.
        A text has them as {name}."""
        values: dict[str, dict[str, Any]] = {}
        for kind in kinds:
            if kind.name not in LIST_TYPES.get(event, ()):
                continue
            for value in kind.values:
                one = values.setdefault(value.name, {"name": value.name, "aka": [], "default": value.default})
                one["aka"] = list(dict.fromkeys((*one["aka"], *value.also_known_as)))
        return list(values.values())

    @staticmethod
    def old_codes(text: str, event: str) -> str:
        """A text of the first event lists ({event.data.username} followed) with the values' names
        ({user} followed); {event.data.time} (no event had it) is gone."""
        def name(found: re.Match[str]) -> str:
            key = found.group(1)
            key = OLD_AMOUNTS.get(event, key) if key == "amount" else OLD_KEYS.get(key, key)
            return f"{{{key}}}" if key else ""
        return OLD_CODE.sub(name, text)

    @staticmethod
    def to_words(text: str, names: list[tuple[str, str]] | None = None) -> str:
        """{session.twitch.follower-latest.name} → [Latest follower]; names: those (name, code) instead."""
        names = {code: name for name, code in (names if names is not None else (*ALWAYS, *ALERT))}
        return CODE.sub(lambda found: f"[{names[found.group(0)]}]" if found.group(0) in names else found.group(0),
                        text)

    @staticmethod
    def to_codes(text: str, names: list[tuple[str, str]] | None = None) -> str:
        """[Latest follower] → {session.twitch.follower-latest.name}; [anything else] stays."""
        codes = {name.casefold(): code for name, code in (names if names is not None else (*ALWAYS, *ALERT))}
        return WORD.sub(lambda found: codes.get(found.group(1).strip().casefold(), found.group(0)), text)

    @staticmethod
    def fill(text: str, session: dict[str, Any]) -> list[tuple[str, bool]]:
        """The text in parts: (words, True for a filled-in value)."""
        parts: list[tuple[str, bool]] = []
        for number, piece in enumerate(CODE.split(text)):
            if number % 2 == 0:
                if piece:
                    parts.append((piece, False))
                continue
            parts.append((_value(piece, session), True))
        return parts

    @staticmethod
    def list_samples(settings: dict[str, Any]) -> list[dict[str, Any]]:
        """What the editor's canvas shows in an event list (ElementDesign.event_list): three example events, of
        the events it shows in turn, the newest last (in the order they would have come)."""
        entries = [entry for entry in settings.get("entries") or [] if entry.get("on", True)]
        if not entries:
            return []
        samples = []
        for nth in range(min(3, settings.get("count") or 3)):
            entry = entries[nth % len(entries)]
            name = SAMPLE_NAME + ("" if nth == 0 else f" {nth + 1}")
            samples.append({"kind": entry["event"],
                            "data": {**DesignValues.list_sample(entry.get("values") or []), "user": name,
                                     "message": SAMPLE_MESSAGES[nth % len(SAMPLE_MESSAGES)]}})
        return samples

    @staticmethod
    def list_sample(values: list[dict[str, Any]]) -> dict[str, Any]:
        """An example of an entry's values (list_values) for the editor's preview: each value's default, an
        example where that is empty."""
        return {value["name"]: value.get("default") or SAMPLE_VALUES.get(value["name"], "") for value in values}

    @staticmethod
    def ticker(ticker: dict[str, Any], session: dict[str, Any], currency: str = "$") -> list[tuple[str, bool]]:
        """A ticker of the editor's (ElementDesign.ticker) as the canvas shows it: the recent ones' names,
        examples while there are none yet. One round: element.js runs it along, round and round."""
        recent = [entry for entry in session.get(f"{ticker['kind']}-recent") or [] if isinstance(entry, dict)]
        if not recent:
            recent = [{"name": SAMPLE_NAME + ("" if nth == 0 else f" {nth + 1}"), "amount": 5 * (nth + 1)}
                      for nth in range(min(ticker["count"], 5))]
        sign = currency if ticker["kind"] == "tip" else ""
        between = "\n" if ticker["look"] == "lines" else ticker["between"]
        parts: list[tuple[str, bool]] = []
        for nth, entry in enumerate(recent[:ticker["count"]]):
            amount = f" ({sign}{entry.get('amount')})" if ticker["amount"] and entry.get("amount") else ""
            parts.append((str(entry.get("name") or "") + amount, True))
            if ticker["look"] == "run" or nth < min(len(recent), ticker["count"]) - 1:
                parts.append((between, False))
        return parts


def _value(path: str, session: dict[str, Any]) -> str:
    words = path.strip().split(".")
    if words[0] == "event":
        value: Any = {"data": SAMPLE_EVENT}
        words = words[1:]
    elif words[0] == "session":
        value, words = session, words[2:]
    else:
        return ""
    for word in words:
        value = value.get(word) if isinstance(value, dict) else None
    if value in (None, ""):
        return SAMPLE_NAME if path.endswith(".name") else "0"
    return str(value)
