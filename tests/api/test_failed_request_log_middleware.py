import unittest

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from streamer_toolbox.api.failed_request_log_middleware import FailedRequestLogMiddleware

LOGGER = "streamer_toolbox.api.failed_request_log_middleware"


def _fine(request):
    return PlainTextResponse("ok")


def _broken(request):
    raise RuntimeError("index swap failed")


class TestFailedRequestLogMiddleware(unittest.TestCase):
    """His 11-20: the emote pictures that failed (404 / 500) left no trace; now every failed answer is in the log."""

    def setUp(self) -> None:
        self.now = 0.0
        app = Starlette(routes=[Route("/fine", _fine), Route("/broken", _broken)])
        app.add_middleware(FailedRequestLogMiddleware, clock=lambda: self.now)
        self.client = TestClient(app, raise_server_exceptions=False)

    def test_a_good_answer_is_not_written(self) -> None:
        with self.assertNoLogs(LOGGER):
            self.assertEqual(200, self.client.get("/fine").status_code)

    def test_a_missing_file_is_written_without_its_query_and_once_a_minute(self) -> None:
        with self.assertLogs(LOGGER, "WARNING") as seen:
            self.client.get("/toolbox/media/x.png?token=secret123")
            self.client.get("/toolbox/media/x.png")
            self.now += 61
            self.client.get("/toolbox/media/x.png")
        self.assertEqual(["GET /toolbox/media/x.png answered 404"] * 2, [r.getMessage() for r in seen.records])
        self.assertNotIn("secret123", "".join(seen.output))

    def test_an_error_inside_is_written_with_its_traceback(self) -> None:
        with self.assertLogs(LOGGER, "ERROR") as seen:
            self.assertEqual(500, self.client.get("/broken").status_code)
        self.assertEqual("GET /broken failed", seen.records[0].getMessage())
        self.assertIn("index swap failed", seen.output[0])

    def test_the_browsers_icon_is_left_out(self) -> None:
        with self.assertNoLogs(LOGGER):
            self.client.get("/favicon.ico")
