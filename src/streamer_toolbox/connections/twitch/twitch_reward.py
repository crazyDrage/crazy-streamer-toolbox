from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TwitchReward:
    """A channel point reward as the Twitch tool shows and edits it. 0 for cooldown / max_per_stream /
    max_per_user means "no limit". by_toolbox: the toolbox's Twitch app made it, so it may change it, delete it
    and refund its redeems (Twitch's rule); a reward made on the dashboard can only be watched."""

    title: str
    cost: int = 100
    prompt: str = ""
    color: str = "#9147FF"
    enabled: bool = True
    paused: bool = False
    needs_text: bool = False
    skip_queue: bool = False  # redeems are marked done at once: then they can't be refunded any more
    cooldown: int = 0
    max_per_stream: int = 0
    max_per_user: int = 0
    id: str = ""
    by_toolbox: bool = False
    image: str = ""

    @classmethod
    def from_api(cls, data: dict[str, Any], by_toolbox: bool = False) -> "TwitchReward":
        def limit(name: str, value: str) -> int:
            setting = data.get(name) or {}
            return int(setting.get(value, 0)) if setting.get("is_enabled") else 0

        image = data.get("image") or data.get("default_image") or {}
        return cls(str(data.get("title", "")), int(data.get("cost", 0)), str(data.get("prompt", "")),
                   str(data.get("background_color") or "#9147FF"), bool(data.get("is_enabled", True)),
                   bool(data.get("is_paused", False)), bool(data.get("is_user_input_required", False)),
                   bool(data.get("should_redemptions_skip_request_queue", False)),
                   limit("global_cooldown_setting", "global_cooldown_seconds"),
                   limit("max_per_stream_setting", "max_per_stream"),
                   limit("max_per_user_per_stream_setting", "max_per_user_per_stream"),
                   str(data.get("id", "")), by_toolbox, str(image.get("url_2x") or image.get("url_1x") or ""))

    def to_api(self) -> dict[str, Any]:
        """The body Twitch takes to create or update it (the same fields both times)."""
        return {"title": self.title.strip(), "cost": max(1, int(self.cost)), "prompt": self.prompt,
                "background_color": self.color, "is_enabled": self.enabled, "is_paused": self.paused,
                "is_user_input_required": self.needs_text,
                "should_redemptions_skip_request_queue": self.skip_queue,
                "is_global_cooldown_enabled": self.cooldown > 0, "global_cooldown_seconds": max(1, self.cooldown),
                "is_max_per_stream_enabled": self.max_per_stream > 0, "max_per_stream": max(1, self.max_per_stream),
                "is_max_per_user_per_stream_enabled": self.max_per_user > 0,
                "max_per_user_per_stream": max(1, self.max_per_user)}
