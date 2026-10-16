from urllib.parse import quote

import nicegui
from starlette.responses import JSONResponse, RedirectResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from streamer_toolbox.core.security.secret_vault import SecretVault

UNLOCK = "/unlock"
# what a locked toolbox still answers: the page to log in, the sign-in page of another device, NiceGUI's own
# code and socket, our static files. Not the HTTP API: no box runs before the login
OPEN_PATHS = (UNLOCK, "/login", f"/_nicegui/{nicegui.__version__}/", "/_nicegui_ws/", "/static/", "/favicon")
# answered with 423 instead of the login page: the API, and the overlays (a browser source in OBS must never
# show a password field on stream)
API_PATHS = ("/action/", "/actions", "/overlay/")


class SecretsLockMiddleware:
    """While a login is set and the password wasn't typed yet (SecretVault), nothing of the toolbox is
    reachable: every page leads to /unlock, the HTTP API answers 423 (locked). With no login, or after it,
    this lets everything through."""

    def __init__(self, app: ASGIApp, vault: SecretVault) -> None:
        self._app = app
        self._vault = vault

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "/")
        if scope["type"] != "http" or self._vault.unlocked or path.startswith(OPEN_PATHS):
            await self._app(scope, receive, send)
        elif path.startswith(API_PATHS):
            await JSONResponse({"error": "The toolbox is locked: log in on its page first"}, 423)(scope, receive, send)
        else:
            await RedirectResponse(f"{UNLOCK}?next={quote(path)}")(scope, receive, send)
