from collections.abc import Callable
from urllib.parse import parse_qs, quote

import nicegui
from starlette.requests import HTTPConnection
from starlette.responses import RedirectResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from streamer_toolbox.core.security.remote_access import RemoteAccess
from streamer_toolbox.core.security.signed_in_devices import SignedInDevices

# free without signing in: the login page, NiceGUI's own code (only its versioned library files: not
# /_nicegui/client/ uploads nor /_nicegui/auto/ files from this PC), our static files, and the HTTP API (it has
# its own tokens)
OPEN_PATHS = ("/login", f"/_nicegui/{nicegui.__version__}/", "/static/", "/action/", "/actions", "/favicon")
SOCKET_PATH = "/_nicegui_ws/"  # NiceGUI's socket.io: websocket and its http polling fallback


class RemoteLoginMiddleware:
    """A gate in front of everything, for page loads and for websockets alike. This PC always passes. Another
    device passes once signed in (its session cookie's browser id is in SignedInDevices with the current key);
    until then it gets /login, and a socket only for a login page (the page puts its client id in the socket's
    query). So a device that never signed in can't load a page nor talk to one over the socket.

    is_login_client(client_id) tells whether that NiceGUI client shows the login page. Needs NiceGUI's
    SessionMiddleware outside of it (ui.run with a storage_secret adds it after, i.e. around, this one)."""

    def __init__(self, app: ASGIApp, access: RemoteAccess, devices: SignedInDevices,
                 is_login_client: Callable[[str], bool]) -> None:
        self._app = app
        self._access = access
        self._devices = devices
        self._is_login_client = is_login_client

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket") or self._allowed(HTTPConnection(scope)):
            await self._app(scope, receive, send)
        elif scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
        else:
            path = scope.get("path", "/")
            target = "/" if path.startswith(SOCKET_PATH) else path
            await RedirectResponse(f"/login?next={quote(target)}")(scope, receive, send)

    def _allowed(self, connection: HTTPConnection) -> bool:
        if RemoteAccess.is_this_pc(connection.client.host if connection.client else None):
            return True
        session = connection.scope.get("session") or {}
        if self._devices.signed_in(session.get("id"), self._access.session_key() if self._access.has_password
                                   else ""):
            return True
        path = connection.url.path
        if path.startswith(SOCKET_PATH):
            client_id = parse_qs(connection.url.query).get("client_id", [""])[0]
            return self._is_login_client(client_id)
        return path.startswith(OPEN_PATHS)
