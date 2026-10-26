import asyncio
import tempfile
import time
import unittest
from pathlib import Path

from streamer_toolbox.connections.streamerbot.streamerbot_events import authentication, streamerbot_event
from streamer_toolbox.connections.streamerbot_connection import StreamerbotConnection
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.events.event_fields import EVENT_FIELDS
from tests.fakes.fake_json_socket_server import FakeJsonSocketServer

HELLO = {"timestamp": "2026-10-05T10:00:00", "session": "s", "request": "Hello",
         "info": {"instanceId": "i", "name": "Streamer.bot", "version": "1.0.1", "source": "websocketServer"}}
ASKS = {"salt": "c2FsdA==", "challenge": "Y2hhbGxlbmdl"}
EVENTS = {"Twitch": ["Follow", "ChatMessage"], "Kick": ["Follow", "ChatMessage"], "General": ["Custom"]}


def streamerbot(password: str = ""):
    """Answers like Streamer.bot's docs: every answer carries the request's id and a status."""
    def answer(message: dict, path: str) -> dict:
        kind, back = message["request"], {"id": message["id"], "status": "ok"}
        if kind == "Authenticate":
            right = authentication(password, ASKS["salt"], ASKS["challenge"])
            back["status"] = "ok" if message["authentication"] == right else "error"
        elif kind == "GetEvents":
            back["events"] = EVENTS
        elif kind == "Subscribe":
            back["events"] = message["events"]
        elif kind == "GetActions":
            back.update(count=3, actions=[{"enabled": True, "group": "None", "id": "g1", "name": "Hype"},
                                          {"enabled": False, "id": "g2", "name": "Old"},
                                          {"enabled": True, "id": "g3", "name": "Confetti"}])
        elif kind == "GetGlobal":
            back["variable"] = {"name": message["variable"], "value": 7, "lastWrite": "x"}
        elif kind == "SendMessage" and message["platform"] == "twitch" and not password:
            back.update(status="error", error="Authentication required to use this method")  # its words, 10-10
        elif kind == "DoAction" and message["action"]["name"] == "Missing":
            back.update(status="error", error="Action not found")
        return back
    return answer


async def until(check, timeout: float = 3.0) -> None:
    end = time.monotonic() + timeout
    while not check():
        if time.monotonic() > end:
            raise AssertionError("timed out")
        await asyncio.sleep(0.02)


class TestStreamerbotConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.password = Path(self._dir.name) / "streamerbot_password.txt"
        self.events = EventBus()
        self.seen: list[tuple[str, dict]] = []

        async def listen(kind: str, data: dict) -> None:
            self.seen.append((kind, data))

        self.events.subscribe(listen)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _connection(self, url: str, **settings) -> tuple[StreamerbotConnection, ActionRegistry]:
        connection = StreamerbotConnection({"enabled": True, "url": url, **settings}, self.password,
                                           self.events, retry_delay=0.05)
        actions = ActionRegistry()
        connection.add_actions(actions)
        return connection, actions

    def test_the_login_answer_is_the_documented_double_hash(self) -> None:
        # base64(sha256(base64(sha256("pw" + "salt")) + "challenge")), worked out by hand once
        import base64
        import hashlib
        secret = base64.b64encode(hashlib.sha256(b"pwsalt").digest())
        self.assertEqual(authentication("pw", "salt", "challenge"),
                         base64.b64encode(hashlib.sha256(secret + b"challenge").digest()).decode())

    def test_an_events_user_and_message_are_found_where_they_usually_are(self) -> None:
        event = streamerbot_event({"timeStamp": "t", "event": {"source": "Kick", "type": "ChatMessage"},
                                   "data": {"user": {"name": "ann"}, "message": {"message": "hi"}}})
        self.assertEqual(event, {"source": "Kick", "type": "ChatMessage", "user": "ann", "message": "hi",
                                 "data": {"user": {"name": "ann"}, "message": {"message": "hi"}}})
        self.assertEqual(set(event), set(EVENT_FIELDS["streamerbot.event"]))
        bare = streamerbot_event({"event": {"source": "General", "type": "Custom"}, "data": None})
        self.assertEqual((bare["user"], bare["message"], bare["data"]), ("", "", {}))

    async def test_actions_run_by_name_and_only_the_named_categories_are_listened_to(self) -> None:
        async with FakeJsonSocketServer(streamerbot(), [HELLO]) as server:
            connection, actions = self._connection(server.url)
            await connection.start()
            await until(lambda: connection.status.state is ConnectionState.CONNECTED)
            self.assertEqual(connection.status.facts, (("Streamer.bot", "1.0.1"), ("Listening to", "General, Kick")))
            subscribed = next(m for m in server.received if m["request"] == "Subscribe")
            self.assertEqual(subscribed["events"], {"Kick": ["Follow", "ChatMessage"], "General": ["Custom"]})
            self.assertEqual(await actions.get("streamerbot.do_action").options["action"](), ["Confetti", "Hype"])
            await actions.run("streamerbot.do_action", action="Hype", args='{"user": "ann", "count": 2}')
            self.assertEqual({k: server.received[-1][k] for k in ("request", "action", "args")},
                             {"request": "DoAction", "action": {"name": "Hype"},
                              "args": {"user": "ann", "count": 2}})
            self.assertEqual(await actions.run("streamerbot.get_global", variable="deaths"), {"value": 7})
            await actions.run("streamerbot.code_trigger", trigger=" lights ", args='{"color": "red"}')
            self.assertEqual({k: server.received[-1][k] for k in ("request", "triggerName", "args")},
                             {"request": "ExecuteCodeTrigger", "triggerName": "lights", "args": {"color": "red"}})
            with self.assertRaisesRegex(ValueError, "Which trigger"):
                await actions.run("streamerbot.code_trigger", trigger=" ")
            await actions.run("streamerbot.send_chat", message="hi", platform="Kick")
            self.assertEqual((server.received[-1]["platform"], server.received[-1]["bot"]), ("kick", True))
            with self.assertRaisesRegex(PermissionError, "tick Authentication and set a password"):
                await actions.run("streamerbot.send_chat", message="hi")  # no password: Streamer.bot refuses
            with self.assertRaisesRegex(RuntimeError, "Action not found"):
                await actions.run("streamerbot.do_action", action="Missing")
            with self.assertRaises(ValueError):
                await actions.run("streamerbot.do_action", action="Hype", args="ann")
            await server.tell({"timeStamp": "t", "event": {"source": "Kick", "type": "Follow"},
                               "data": {"user": {"name": "bob"}}})
            await until(lambda: len(self.seen) == 1)
            self.assertEqual(self.seen[0][0], "streamerbot.event")
            self.assertEqual((self.seen[0][1]["source"], self.seen[0][1]["user"]), ("Kick", "bob"))
            await connection.stop()

    async def test_a_password_is_answered_and_a_missing_or_wrong_one_stops_it(self) -> None:
        hello = {**HELLO, "authentication": ASKS}
        async with FakeJsonSocketServer(streamerbot("open sesame"), [hello]) as server:
            connection, actions = self._connection(server.url, listen="*")
            await connection.start()
            await until(lambda: connection.status.state is ConnectionState.ERROR)
            self.assertIn("asks for a password", connection.status.detail)
            self.password.write_text("wrong\n", encoding="utf-8")
            await connection.start()
            await until(lambda: connection.status.state is ConnectionState.ERROR)
            self.assertEqual(connection.status.detail, "Streamer.bot refused the password")
            self.password.write_text("open sesame\n", encoding="utf-8")
            await connection.start()
            await until(lambda: connection.status.state is ConnectionState.CONNECTED)
            self.assertEqual(connection.status.facts[1], ("Listening to", "General, Kick, Twitch"))
            self.assertNotIn("open sesame", str(server.received))
            await connection.stop()

    async def test_off_or_not_running_is_said_plainly(self) -> None:
        async with FakeJsonSocketServer(streamerbot(), [HELLO]) as server:
            gone = server.url
        off = StreamerbotConnection({"url": gone}, self.password, self.events)
        self.assertFalse(off.settings["enabled"])
        actions = ActionRegistry()
        off.add_actions(actions)
        with self.assertRaisesRegex(NotConnectedError, "switched off"):
            await actions.run("streamerbot.do_action", action="Hype")
        connection, actions = self._connection(gone)
        await connection.start()
        await until(lambda: connection.status.state is ConnectionState.ERROR)
        with self.assertRaisesRegex(NotConnectedError, "not connected"):
            await actions.run("streamerbot.do_action", action="Hype")
        self.assertEqual(await actions.get("streamerbot.do_action").options["action"](), [])
        await connection.stop()


if __name__ == "__main__":
    unittest.main()
