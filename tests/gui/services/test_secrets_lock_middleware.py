import tempfile
import unittest
from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from streamer_toolbox.core.security.secret_vault import SecretVault
from streamer_toolbox.gui.services.secrets_lock_middleware import SecretsLockMiddleware


class TestSecretsLockMiddleware(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.folder = Path(self._dir.name) / "secrets"

        async def page(request) -> PlainTextResponse:
            return PlainTextResponse(f"open {request.url.path}")

        paths = ("/", "/flows", "/unlock", "/login", "/actions", "/overlay/alerts", "/static/app.css")
        self.app = Starlette(routes=[Route(path, page) for path in paths])
        self.vault = SecretVault(self.folder)
        self.client = TestClient(SecretsLockMiddleware(self.app, self.vault), follow_redirects=False)

    def test_without_a_login_everything_passes(self) -> None:
        self.assertEqual("open /flows", self.client.get("/flows").text)
        self.assertEqual("open /actions", self.client.get("/actions").text)

    def test_locked_pages_lead_to_the_login_and_the_api_and_overlays_say_locked(self) -> None:
        self.vault.set_login("correct horse")
        locked = SecretVault(self.folder)  # a new start
        client = TestClient(SecretsLockMiddleware(self.app, locked), follow_redirects=False)

        answer = client.get("/flows")
        self.assertEqual((307, "/unlock?next=/flows"), (answer.status_code, answer.headers["location"]))
        self.assertEqual(423, client.get("/actions").status_code)
        self.assertEqual(423, client.get("/overlay/alerts").status_code)
        for free in ("/unlock", "/login", "/static/app.css"):
            self.assertEqual(f"open {free}", client.get(free).text)

        locked.unlock("correct horse")
        self.assertEqual("open /flows", client.get("/flows").text)


if __name__ == "__main__":
    unittest.main()
