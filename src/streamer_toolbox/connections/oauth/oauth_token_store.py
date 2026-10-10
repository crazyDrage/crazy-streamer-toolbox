import json
from pathlib import Path

from streamer_toolbox.connections.oauth.oauth_token import OAuthToken


class OAuthTokenStore:
    """A login, kept in its own file next to the settings (config/twitch_token.json, config/youtube_token.json),
    never in toolbox.toml."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> OAuthToken | None:
        if not self._path.exists():
            return None
        try:
            return OAuthToken.from_dict(json.loads(self._path.read_text(encoding="utf-8")))
        except (ValueError, KeyError):
            return None

    def save(self, token: OAuthToken) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(token.to_dict(), indent=1), encoding="utf-8")

    def clear(self) -> None:
        self._path.unlink(missing_ok=True)
