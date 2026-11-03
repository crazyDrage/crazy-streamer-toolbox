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
        self.assertEqual(self.queue.overlays, 0)

    def test_a_quiet_line_says_alive_so_the_page_knows_it_still_works(self) -> None:
        """His round 64: a line that dropped without a word left the page waiting forever."""
        app = FastAPI()
        app.include_router(build_overlay_router(self.queue, heartbeat=0.05))
        with TestClient(app).websocket_connect("/overlay/alerts/ws") as socket:
            self.assertEqual(socket.receive_json()["type"], "hello")
            self.assertEqual(socket.receive_json(), {"type": "alive"})
            self.queue.clear()
            self.assertEqual(socket.receive_json(), {"type": "clear", "id": 1})

    def test_a_page_that_comes_back_says_its_last_id_and_gets_the_rest(self) -> None:
        self.queue.clear()
        self.queue.clear()
        run = self.queue.sent.run
        with self.client.websocket_connect(f"/overlay/alerts/ws?run={run}&after=1") as socket:
            self.assertEqual(socket.receive_json(), {"type": "hello", "run": run, "last": 2})
            self.assertEqual(socket.receive_json(), {"type": "clear", "id": 2})


if __name__ == "__main__":
    unittest.main()
