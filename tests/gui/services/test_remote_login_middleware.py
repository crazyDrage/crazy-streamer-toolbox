import tempfile
import unittest
from pathlib import Path

import nicegui
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route, WebSocketRoute
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from streamer_toolbox.core.config.config_table_writer import ConfigTableWriter
from streamer_toolbox.core.security.remote_access import RemoteAccess
from streamer_toolbox.core.security.signed_in_devices import SignedInDevices
from streamer_toolbox.gui.services.remote_login_middleware import RemoteLoginMiddleware

LIBRARY = f"/_nicegui/{nicegui.__version__}/static/vue.js"


async def socket(websocket) -> None:
    await websocket.accept()
    await websocket.send_text("hello")
    await websocket.close()


class TestRemoteLoginMiddleware(unittest.TestCase):
    """The gate for page loads and NiceGUI's socket (/_nicegui_ws/...), with a fake signed session cookie."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.access = RemoteAccess({}, {}, ConfigTableWriter(Path(self.tmp.name) / "toolbox.toml"))
        self.access.set_password("long enough")
        self.devices = SignedInDevices(Path(self.tmp.name) / "devices.json")
        self.browser = "browser-1"
        paths = ("/", "/settings", "/login", "/action/x", LIBRARY, "/_nicegui/client/c1/upload/u1",
                 "/_nicegui/auto/static/t/secret.png", "/_nicegui_ws/socket.io/")
        app = Starlette(routes=[Route(p, lambda r: PlainTextResponse("page"), methods=["GET", "POST"]) for p in paths]
                        + [WebSocketRoute("/_nicegui_ws/socket.io/", socket)])
        app.add_middleware(RemoteLoginMiddleware, access=self.access, devices=self.devices,
                           is_login_client=lambda client_id: client_id == "login-client")
        self.app = self._with_session(app)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _with_session(self, inner):
        async def app(scope, receive, send):  # what NiceGUI's SessionMiddleware puts in the scope
            if scope["type"] in ("http", "websocket"):
                scope["session"] = {"id": self.browser}
            await inner(scope, receive, send)
        return app

    def client(self, host: str) -> TestClient:
        return TestClient(self.app, client=(host, 5000))

    def get(self, host: str, path: str):
        return self.client(host).get(path, follow_redirects=False)

    def open_socket(self, host: str, client_id: str) -> str:
        with self.client(host).websocket_connect(f"/_nicegui_ws/socket.io/?client_id={client_id}") as ws:
            return ws.receive_text()

    def test_this_pc_never_signs_in(self) -> None:
        self.assertEqual(self.get("127.0.0.1", "/settings").text, "page")
        self.assertEqual(self.open_socket("127.0.0.1", "any-client"), "hello")

    def test_another_device_goes_to_login_until_signed_in_with_the_current_password(self) -> None:
        answer = self.get("192.168.1.20", "/settings")
        self.assertEqual((answer.status_code, answer.headers["location"]), (307, "/login?next=/settings"))
        for path in ("/login", "/action/x", LIBRARY):  # the login page, its code, the API (own tokens)
            self.assertEqual(self.get("192.168.1.20", path).text, "page", path)
        self.devices.add(self.browser, self.access.session_key())
        self.assertEqual(self.get("192.168.1.20", "/settings").text, "page")
        self.access.set_password("a new one!")
        self.assertEqual(self.get("192.168.1.20", "/").status_code, 307)

    def test_uploads_and_files_under_nicegui_stay_closed(self) -> None:
        for path in ("/_nicegui/client/c1/upload/u1", "/_nicegui/auto/static/t/secret.png"):
            self.assertEqual(self.get("192.168.1.20", path).status_code, 307, path)

    def test_a_device_that_never_signed_in_gets_a_socket_only_for_the_login_page(self) -> None:
        self.assertEqual(self.open_socket("192.168.1.20", "login-client"), "hello")
        for client_id in ("settings-client", ""):
            with self.assertRaises(WebSocketDisconnect):
                self.open_socket("192.168.1.20", client_id)
        polling = self.get("192.168.1.20", "/_nicegui_ws/socket.io/?client_id=settings-client&transport=polling")
        self.assertEqual(polling.status_code, 307)  # socket.io's http fallback: same rule
        self.assertEqual(self.get("192.168.1.20", "/_nicegui_ws/socket.io/?client_id=login-client").text, "page")
        self.devices.add(self.browser, self.access.session_key())
        self.assertEqual(self.open_socket("192.168.1.20", "settings-client"), "hello")

    def test_another_browser_on_a_signed_in_device_still_signs_in(self) -> None:
        self.devices.add("browser-2", self.access.session_key())
        self.assertEqual(self.get("192.168.1.20", "/settings").status_code, 307)
