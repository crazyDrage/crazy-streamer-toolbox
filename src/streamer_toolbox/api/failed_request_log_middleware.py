import logging
import time
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

log = logging.getLogger(__name__)

QUIET_SECONDS = 60.0  # the same path and answer is written once a minute at most
NOT_WORTH = ("/favicon.ico",)


class FailedRequestLogMiddleware(BaseHTTPMiddleware):
    """Writes each request the toolbox answered with an error (4xx / 5xx) into the log, and an error inside a
    page or route with its traceback (his 11-20: the emotes that failed on the first loads left no trace).

    Only the method and the path: never the query (a token or key can be in it). A widget that asks for a
    missing file on every load would fill the log, so the same path and answer is written once a minute."""

    def __init__(self, app: ASGIApp, clock: Callable[[], float] = time.monotonic) -> None:
        super().__init__(app)
        self._clock = clock
        self._last: dict[tuple[str, str, int], float] = {}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            response = await call_next(request)
        except Exception:
            log.exception("%s %s failed", request.method, request.url.path)
            raise
        if response.status_code >= 400 and request.url.path not in NOT_WORTH:
            self._tell(request.method, request.url.path, response.status_code)
        return response

    def _tell(self, method: str, path: str, status: int) -> None:
        key, now = (method, path, status), self._clock()
        if now - self._last.get(key, float("-inf")) < QUIET_SECONDS:
            return
        if len(self._last) > 1000:  # many different paths: start the memory again
            self._last.clear()
        self._last[key] = now
        log.warning("%s %s answered %s", method, path, status)
