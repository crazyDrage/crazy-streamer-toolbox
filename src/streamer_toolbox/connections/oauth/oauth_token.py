import time
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class OAuthToken:
    """A user access token of the streamer's account at a service (Twitch, YouTube), with what's needed to
    renew it."""

    access_token: str
    refresh_token: str
    expires_at: float          # unix time
    scopes: tuple[str, ...]
    user_id: str = ""
    login: str = ""

    @classmethod
    def from_answer(cls, answer: dict[str, Any], user_id: str = "", login: str = "") -> "OAuthToken":
        """From a token answer (access_token, refresh_token, expires_in, scope as a list: Twitch's shape)."""
        return cls(answer["access_token"], answer.get("refresh_token", ""),
                   time.time() + float(answer.get("expires_in", 3600)), tuple(answer.get("scope", [])),
                   user_id, login)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OAuthToken":
        return cls(data["access_token"], data["refresh_token"], float(data["expires_at"]),
                   tuple(data.get("scopes", ())), data.get("user_id", ""), data.get("login", ""))

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "scopes": list(self.scopes)}

    def expires_soon(self, margin: float = 120) -> bool:
        return time.time() > self.expires_at - margin
