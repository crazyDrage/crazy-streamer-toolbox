import json
from typing import Any

import httpx

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.box_value import to_bool, to_kind, understand

METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]


class HttpActions:
    """Web requests (SAMMI's HTTP Request), e.g. a vibration board's REST API on the home network.
    The answer comes back as {status, ok, body}; a JSON body is already turned into a list / object."""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport  # tests answer without a network

    def add_to(self, actions: ActionRegistry) -> None:
        async def methods() -> list[str]:
            return METHODS

        actions.add("web.request", self.request, "Sends a web request (GET, POST, ...) and gives back the answer: "
                    "status (200 = fine), ok, body (JSON already read). query = an object or a=1&b=2 for after "
                    "the ?; body = an object (sent as JSON) or text; headers = an object. Fails on status 400 and "
                    "up unless fail_on_error is off", "Web request", group="Request", options={"method": methods},
                    flow_only=True, outputs={"status": "number", "ok": "yes/no", "body": "any"})

    async def request(self, url: str, method: str = "GET", query: Any = "", body: Any = "", headers: Any = "",
                      seconds: float = 10.0, fail_on_error: bool = True) -> dict[str, Any]:
        method = str(method).upper()
        if method not in METHODS:
            raise ValueError(f"method must be one of {', '.join(METHODS)}, not {method!r}")
        if not str(url).startswith(("http://", "https://")):
            raise ValueError(f"the address must start with http:// or https://, not {url!r}")
        content, kind = _body(body)
        sent_headers = {str(k): str(v) for k, v in _object(headers, "headers").items()}
        if kind and not any(k.casefold() == "content-type" for k in sent_headers):
            sent_headers["Content-Type"] = kind
        async with httpx.AsyncClient(transport=self._transport, timeout=float(seconds)) as client:
            try:
                answer = await client.request(method, str(url), params=_query(query), content=content,
                                              headers=sent_headers)
            except httpx.TimeoutException:
                raise TimeoutError(f"{url} didn't answer within {float(seconds):g} s") from None
            except httpx.HTTPError as e:
                raise ConnectionError(f"can't reach {url}: {e}") from None
        if answer.status_code >= 400 and to_bool(fail_on_error):
            raise RuntimeError(f"{method} {url} answered {answer.status_code}: {answer.text[:200]}")
        return {"status": answer.status_code, "ok": answer.is_success, "body": understand(answer.text)}


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
