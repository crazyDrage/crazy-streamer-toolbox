import re
from typing import Any

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
    def to_words(text: str) -> str:
        """{session.twitch.follower-latest.name} → [Latest follower]."""
        names = {code: name for name, code in (*ALWAYS, *ALERT)}
        return CODE.sub(lambda found: f"[{names[found.group(0)]}]" if found.group(0) in names else found.group(0),
                        text)

    @staticmethod
    def to_codes(text: str) -> str:
        """[Latest follower] → {session.twitch.follower-latest.name}; [anything else] stays."""
        codes = {name.casefold(): code for name, code in (*ALWAYS, *ALERT)}
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
