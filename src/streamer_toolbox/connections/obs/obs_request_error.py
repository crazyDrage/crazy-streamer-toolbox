# obs-websocket's RequestStatus codes (docs/generated/protocol.md) in words; the rest keep only the code
MEANINGS = {
    203: "the request has no type",
    204: "OBS doesn't know this request (an older OBS?)",
    205: "OBS reported an error",
    207: "OBS isn't ready yet",
    300: "a field it needs is missing",
    301: "the request has no data",
    400: "a field has a value OBS doesn't accept",
    401: "a field has the wrong kind of value",
    402: "a number is outside the range OBS allows",
    403: "a field is empty and must not be",
    404: "too many fields are set at once",
    500: "that can't be done while it is running",
    502: "it is paused and shouldn't be",
    503: "it isn't paused",
    504: "that output is switched off in OBS",
    505: "studio mode is on and must be off for this",
    506: "studio mode must be on for this",
    600: "OBS has nothing with that name",
    601: "something with that name exists already",
    602: "that is the wrong kind of thing for this",
    603: "OBS doesn't have enough of them",
    604: "it can't be used right now",
    605: "that source is the wrong kind for this",
    606: "that can't be configured",
    607: "that filter is the wrong kind for this",
    700: "OBS couldn't create it",
    701: "OBS couldn't do that",
    702: "OBS failed to process the request",
    703: "these fields can't be used together",
}
# 501 OutputNotRunning: which output, from the request's name
NOT_RUNNING = (("ReplayBuffer", "the replay buffer isn't running"), ("VirtualCam", "the virtual camera isn't on"),
               ("Record", "OBS isn't recording right now"), ("Stream", "OBS isn't streaming right now"))


class ObsRequestError(Exception):
    """An obs-websocket request was answered with a failure status. The message says what it means in words first,
    then OBS's own comment (if any), the request and the code."""

    def __init__(self, request_type: str, code: int, comment: str | None) -> None:
        super().__init__(f"{_meaning(request_type, code)}{f': {comment}' if comment else ''} "
                         f"({request_type}, OBS code {code})")
        self.request_type = request_type
        self.code = code
        self.comment = comment


def _meaning(request_type: str, code: int) -> str:
    if code == 501:
        return next((text for part, text in NOT_RUNNING if part in request_type), "that output isn't running")
    return MEANINGS.get(code, "OBS said no")
