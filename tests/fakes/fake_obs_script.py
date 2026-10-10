import simpleobsws


class FakeObsScript:
    """OBS answering from a script: per request type a dict (always that), a list of dicts (one per call, the
    last one repeats) or None in the list / as the answer for a failure (code 600, not found)."""

    def __init__(self, responses: dict[str, dict | list | None] | None = None) -> None:
        self.responses = dict(responses or {})
        self.calls: list[tuple[str, dict]] = []

    def kinds(self) -> list[str]:
        return [kind for kind, _ in self.calls]

    def sent(self, kind: str) -> list[dict]:
        return [data for k, data in self.calls if k == kind]

    async def call(self, request: simpleobsws.Request, timeout: int = 15) -> simpleobsws.RequestResponse:
        kind = request.requestType
        self.calls.append((kind, request.requestData or {}))
        answer = self.responses.get(kind, {})
        if isinstance(answer, list):
            answer = answer.pop(0) if len(answer) > 1 else answer[0]
        if answer is None:
            return simpleobsws.RequestResponse(kind, simpleobsws.RequestStatus(False, 600, "not found"))
        return simpleobsws.RequestResponse(kind, simpleobsws.RequestStatus(True, 100), answer)
