from typing import Any


class FakeVtsRequests:
    """VTube Studio's API from a script: answers by message type (a missing one answers {}), every request kept
    with its data and the loop time it was sent at."""

    def __init__(self, answers: dict[str, dict] | None = None, clock: Any = None) -> None:
        self.answers = dict(answers or {})
        self.calls: list[tuple[str, dict]] = []
        self.times: list[float] = []
        self._clock = clock

    async def __call__(self, message_type: str, data: dict | None = None) -> dict[str, Any]:
        self.calls.append((message_type, data or {}))
        if self._clock is not None:
            self.times.append(self._clock())
        return self.answers.get(message_type, {})

    def sent(self, message_type: str) -> list[dict]:
        return [data for kind, data in self.calls if kind == message_type]
