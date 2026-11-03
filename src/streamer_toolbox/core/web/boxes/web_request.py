from typing import Any

import httpx

from streamer_toolbox.core.actions.fixed_choices import fixed_choices
from streamer_toolbox.core.data.box_value import to_bool, understand
from streamer_toolbox.core.web.boxes.http_box import HttpBox, METHODS, _body, _object, _query
from streamer_toolbox.core.web.web_client import web_client


class WebRequest(HttpBox):
    name = "request"
    label = "Web request"
    help = "Sends a web request (GET, POST, ...) and gives back the answer: status (200 = fine), ok, body (JSON " \
           "already read). query = an object or a=1&b=2 for after the ?; body = an object (sent as JSON) or " \
           "text; headers = an object. Fails on status 400 and up unless fail_on_error is off"
    group = "Request"
    options = {"method": fixed_choices(METHODS)}
    flow_only = True
    outputs = {"status": "number", "ok": "yes/no", "body": "any"}

    async def run(self, url: str, method: str = "GET", query: Any = "", body: Any = "", headers: Any = "",
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
        async with web_client(self._transport, timeout=float(seconds)) as client:
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
