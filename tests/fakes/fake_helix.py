from typing import Any

from streamer_toolbox.connections.twitch.twitch_api_error import TwitchApiError


class FakeHelix:
    """Twitch's Helix API from a script: answers by (method, path); a missing one answers {} (204 No Content),
    a TwitchApiError in the script is raised. Every call is kept with its params and body."""

    def __init__(self, answers: dict[tuple[str, str], Any] | None = None) -> None:
        self.answers = dict(answers or {})
        self.calls: list[tuple[str, str, dict, dict]] = []

    async def __call__(self, method: str, path: str, params: dict | None = None, json: dict | None = None,
                       **_: Any) -> dict[str, Any]:
        self.calls.append((method, path, dict(params or {}), dict(json or {})))
        answer = self.answers.get((method, path), {})
        if callable(answer):
            answer = answer(dict(params or {}))
        if isinstance(answer, TwitchApiError):
            raise answer
        return answer

    def sent(self, method: str, path: str) -> list[tuple[dict, dict]]:
        return [(params, body) for m, p, params, body in self.calls if (m, p) == (method, path)]
