import httpx


def web_error(error: httpx.HTTPError) -> str:
    """A failed request in a few words for people: "404 Not Found", "no connection (getaddrinfo failed)".
    httpx's own text for a status names the whole address and a link to read up on the status."""
    if isinstance(error, httpx.HTTPStatusError):
        return f"{error.response.status_code} {error.response.reason_phrase}".strip()
    if isinstance(error, httpx.TimeoutException):
        return "no answer in time"
    if isinstance(error, httpx.ConnectError):
        return f"no connection ({error})" if str(error) else "no connection"
    return str(error) or type(error).__name__
