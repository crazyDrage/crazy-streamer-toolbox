import json
from typing import Any

import httpx

from streamer_toolbox.core.data.box_value import to_kind, understand
from streamer_toolbox.core.interfaces.box import Box


METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]


class HttpBox(Box):
    """What the http boxes share (not a box itself: it has no run).

    Web requests (SAMMI's HTTP Request), e.g. a vibration board's REST API on the home network.
    The answer comes back as {status, ok, body}; a JSON body is already turned into a list / object."""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport  # tests answer without a network


def _object(value: Any, what: str) -> dict[str, Any]:
    if value is None or value == "":
        return {}
    try:
        return to_kind(value, "object")
    except ValueError:
        raise ValueError(f"{what} must be an object like {{\"name\": \"value\"}}, not {value!r}") from None


def _query(value: Any) -> Any:
    """An object, or text like a=1&b=2 (httpx takes both)."""
    if value is None or value == "":
        return None
    understood = understand(value)
    return understood if isinstance(understood, dict) else str(value).lstrip("?")


def _body(value: Any) -> tuple[bytes | None, str]:
    if value is None or value == "":
        return None, ""
    understood = understand(value)
    if isinstance(understood, (dict, list)):
        return json.dumps(understood, ensure_ascii=False).encode(), "application/json"
    return str(value).encode(), "text/plain; charset=utf-8"
