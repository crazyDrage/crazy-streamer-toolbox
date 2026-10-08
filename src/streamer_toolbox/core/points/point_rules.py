from dataclasses import asdict, dataclass, fields
from typing import Any

# chat bots that sit in most channels: they'd collect points with the lurkers
BOTS = "streamelements, nightbot, moobot, streamlabs, fossabot, wizebot, soundalerts, sery_bot, mixitupapp"


@dataclass(frozen=True)
class PointRules:
    """How viewers earn points, kept as `[points]` in toolbox.toml. Off until switched on.

    - `per_time` every `minutes` to everyone who wrote in chat since the last payout, and with `lurkers` on
      also to everyone Twitch lists as being in chat (those who watch and never write). `only_live`: only
      while the stream is on.
    - one-time bonuses: `on_follow`, `on_sub`, `on_raid`, and `per_100_bits` for a cheer.
    - `never`: names that never earn (bots), separated by commas; `streamer_earns`: whether he himself does.
      Both count for the time points and the bonuses; the boxes can still give them points.
    - `source`: where the points live: "toolbox" (its own store; the rules above give them out) or "mixitup"
      (Mix It Up's currency `mixitup_currency`; Mix It Up gives them out by its own rules, the toolbox gives
      none, and the boxes and the command read and change Mix It Up's numbers).
    - `command`: a chat command that answers with the viewer's points ("" = none), `answer`: the words, with
      {user}, {points} and {name}."""

    enabled: bool = False
    name: str = "points"
    per_time: int = 10
    minutes: int = 10
    only_live: bool = True
    lurkers: bool = True
    never: str = BOTS
    streamer_earns: bool = False
    on_follow: int = 50
    on_sub: int = 500
    on_raid: int = 100
    per_100_bits: int = 100
    source: str = "toolbox"
    mixitup_currency: str = ""
    command: str = "!points"
    answer: str = "{user} has {points} {name}"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PointRules":
        start, found = cls(), {}
        for field in fields(cls):
            value = data.get(field.name, getattr(start, field.name))
            kind = type(getattr(start, field.name))
            try:
                if kind is bool:
                    value = value if isinstance(value, bool) else str(value).strip().casefold() in ("true", "1", "yes")
                else:
                    value = kind(value)
            except (TypeError, ValueError):
                value = getattr(start, field.name)
            found[field.name] = max(0, value) if kind is int else value
        found["minutes"] = max(1, found["minutes"])
        found["name"] = found["name"].strip() or "points"
        found["source"] = found["source"] if found["source"] in ("toolbox", "mixitup") else "toolbox"
        return cls(**found)

    def left_out(self) -> set[str]:
        """The names in `never`, small letters."""
        return {name.strip().lstrip("@").casefold() for name in self.never.split(",") if name.strip()}

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
