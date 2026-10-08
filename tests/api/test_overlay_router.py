import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from streamer_toolbox.api.overlay_router import build_overlay_router
from streamer_toolbox.core.alerts.alert import Alert
from streamer_toolbox.core.alerts.alert_queue import AlertQueue


class TestOverlayRouter(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.queue = AlertQueue()
        app = FastAPI()
        app.include_router(build_overlay_router(self.queue))
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_the_page_is_plain_and_not_cached(self) -> None:
        page = self.client.get("/overlay/alerts")
        self.assertEqual(page.status_code, 200)
        self.assertIn("/static/overlay/alerts.js", page.text)
        self.assertEqual(page.headers["cache-control"], "no-store")

    def test_a_file_only_under_the_name_the_queue_gave_it(self) -> None:
        picture = Path(self._dir.name) / "party.png"
        picture.write_bytes(b"png-bytes")
        url = self.queue.payload(Alert(image=str(picture)))["image"]
        self.assertEqual(self.client.get(url).content, b"png-bytes")
        self.assertEqual(self.client.get("/overlay/file/party.png").status_code, 404)
        self.assertEqual(self.client.get("/overlay/file/..%2F..%2Ftoolbox.toml").status_code, 404)

    def test_a_page_listens_while_its_socket_is_open(self) -> None:
        with self.client.websocket_connect("/overlay/alerts/ws"):
            self.assertEqual(self.queue.overlays, 1)


if __name__ == "__main__":
    unittest.main()
