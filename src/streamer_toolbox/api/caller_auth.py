import hmac
from typing import Optional

from streamer_toolbox.api.caller import Caller

LOOPBACK = {"127.0.0.1", "::1", "localhost"}


class CallerAuth:
    """Works out which configured caller a request comes from."""

    def __init__(self, callers: list[Caller]) -> None:
        self._callers = callers

    def identify(self, token: Optional[str], client_host: Optional[str]) -> Optional[Caller]:
        """The caller owning the token, or the local caller for a tokenless request from this PC.

        A wrong token is never retried as local, so a typo shows up as 401 instead of silently passing.
        """
        if token:
            for caller in self._callers:
                if caller.token and hmac.compare_digest(caller.token.encode(), token.encode()):
                    return caller
            return None
        if client_host in LOOPBACK:
            return next((c for c in self._callers if c.local), None)
        return None
