import re
from dataclasses import dataclass, field
from typing import Any

from streamer_toolbox.core.events.event_fields import CHAT_ROLES

WORDS = "words"
WHO = "who"  # {"who": "mod"}: only mods and the broadcaster (the event's "role" must be at least this)
# an id key stands in for its name key: a redeem trigger with reward_id matches by id (a renamed reward still fits)
ID_KEYS = {"reward_id": "reward"}
REWARDS = "twitch.rewards"  # the toolbox's own event when Twitch connects: {"rewards": [{"id", "title"}, ...]}


@dataclass(frozen=True)
class FlowTrigger:
    """Something that starts a flow besides its button, e.g. kind "twitch.redeem" with match {"reward": "..."}.

    A trigger matches an event of the same kind whose data has every key/value in `match`, ignoring upper/lower
    case. A * stands for any text, like in SAMMI: {"message": "!qa *"} matches "!qa how are you?".
    The key "words" is special: {"words": "gay, bl"} matches a message that has one of those as a whole word;
    so is "who": {"who": "vip"} matches a chat message from a VIP, mod or the broadcaster.
    A redeem trigger saved with reward_id matches by that id only (its "reward" name is kept for showing and is
    updated when the reward is renamed on Twitch).
    """

    kind: str
    match: dict[str, Any] = field(default_factory=dict)

    def matches(self, kind: str, data: dict[str, Any]) -> bool:
        skipped = {ID_KEYS[k] for k, v in self.match.items() if k in ID_KEYS and v}
        return kind == self.kind and all(_fits(k, str(v), data) for k, v in self.match.items()
                                         if k not in skipped and (k not in ID_KEYS or v))


def _same(value: str, wanted: str) -> bool:
    if "*" not in wanted:
        return value.casefold() == wanted.casefold()
    pattern = ".*".join(re.escape(part) for part in wanted.casefold().split("*"))
    return re.fullmatch(pattern, value.casefold(), re.DOTALL) is not None


def _has_word(message: str, words: str) -> bool:
    """One of the comma-separated words (or phrases) stands on its own in the message: "bl" is in "bl lol" and
    "so bl!", not in "blue"."""
    wanted = [w.strip().casefold() for w in words.split(",") if w.strip()]
    return any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", message.casefold()) for w in wanted)


def _fits(key: str, wanted: str, data: dict[str, Any]) -> bool:
    if key in ID_KEYS:
        return str(data.get(key, "")) == wanted
    if key == WORDS:
        return _has_word(str(data.get("message", "")), wanted)
    if key == WHO:
        return _rank(str(data.get("role", "viewer"))) >= _rank(wanted)
    return _same(str(data.get(key, "")), wanted)


def _rank(role: str) -> int:
    return CHAT_ROLES.index(role) if role in CHAT_ROLES else 0
