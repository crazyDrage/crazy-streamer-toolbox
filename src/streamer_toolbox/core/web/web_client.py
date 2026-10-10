import functools
import ssl
from typing import Any

import httpx


@functools.cache
def shared_ssl_context() -> ssl.SSLContext:
    """The one SSL context every web client of the toolbox uses (httpx's own default one, made once)."""
    return httpx.create_ssl_context()


def web_client(transport: httpx.AsyncBaseTransport | None = None, **options: Any) -> httpx.AsyncClient:
    """An httpx.AsyncClient for one request or a few, the way the toolbox makes them all over
    (`async with web_client(self._transport, timeout=10) as client:`).

    Why not httpx.AsyncClient(...) itself: a new client builds a new SSL context, and that reads every root
    certificate again, about 0.2 s of processor each time (measured 2026-10-09). The YouTube connection alone
    did that once a minute while idle, and every Twitch call did it too. With the shared context a new client
    costs half a millisecond. A transport given (the tests' fake one) is used as it is."""
    if transport is None:
        options.setdefault("verify", shared_ssl_context())
    return httpx.AsyncClient(transport=transport, **options)
