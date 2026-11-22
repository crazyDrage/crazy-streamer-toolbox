import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from streamer_toolbox.api.inbound_router import build_inbound_router
from tests.fakes.fake_message_inbox import FakeMessageInbox


class TestInboundRouter(unittest.TestCase):
    """A program connects to /connections/<id>/in/<type>?key=... and its messages reach that connection."""

    def setUp(self) -> None:
        self.inbox = FakeMessageInbox()
        app = FastAPI()
        app.include_router(build_inbound_router(lambda connection_id: self.inbox if connection_id == "warudo"
                                                else None))
        self.client = TestClient(app)

    def test_messages_arrive_with_the_type_from_the_address(self) -> None:
        with self.client.websocket_connect("/connections/warudo/in/camera?key=right") as socket:
            socket.send_text('{"x": 1}')
            socket.send_bytes("hä".encode())
        self.assertEqual(self.inbox.said, [("opened", "camera", ""), ("received", "camera", '{"x": 1}'),
                                           ("received", "camera", "hä"), ("closed", "camera", "")])

    def test_several_types_can_be_open_at_once(self) -> None:
        with self.client.websocket_connect("/connections/warudo/in/camera?key=right") as camera, \
                self.client.websocket_connect("/connections/warudo/in/wave?key=right") as wave:
            camera.send_text("1")
            wave.send_text("2")
        self.assertIn(("received", "camera", "1"), self.inbox.said)
        self.assertIn(("received", "wave", "2"), self.inbox.said)

    def test_a_wrong_or_missing_key_and_an_unknown_connection_are_refused(self) -> None:
        for path in ("/connections/warudo/in/camera?key=wrong", "/connections/warudo/in/camera",
                     "/connections/obs/in/camera?key=right"):
            with self.subTest(path=path), self.assertRaises(WebSocketDisconnect) as refused:
                with self.client.websocket_connect(path):
                    pass
            self.assertEqual(refused.exception.code, 1008)
        self.assertEqual(self.inbox.said, [])


if __name__ == "__main__":
    unittest.main()
