import json
import unittest

import httpx

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.connections.sammi_connection import SammiConnection


class TestSammiConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.requests: list[httpx.Request] = []
        self.password_needed = ""

    def _sammi(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.password_needed and request.headers.get("Authorization") != self.password_needed:
            return httpx.Response(401, json={"error": "Unauthorized"})
        return httpx.Response(200, json={"data": "x64" if request.method == "GET" else "Ok."})

    def _connection(self, **settings) -> SammiConnection:
        return SammiConnection({"enabled": True, **settings}, lambda: ("{}", 0), httpx.MockTransport(self._sammi))

    async def test_start_reads_a_variable(self) -> None:
        connection = self._connection()
        await connection.start()
        self.assertEqual(connection.status.state, ConnectionState.CONNECTED)
        self.assertEqual(str(self.requests[0].url),
                         "http://127.0.0.1:9450/api?request=getVariable&name=Architecture")

    async def test_wrong_password_is_explained(self) -> None:
        self.password_needed = "secret"
        status = await self._connection().test({"url": "http://127.0.0.1:9450", "password": "nope"})
        self.assertEqual((status.state, status.detail),
                         (ConnectionState.ERROR, "SAMMI wants a password (or the password is wrong)"))

    async def test_trigger_button_action_posts_request_with_password(self) -> None:
        self.password_needed = "secret"
        actions = ActionRegistry()
        self._connection(password="secret").add_actions(actions)
        self.assertEqual(await actions.run("sammi.trigger_button", button_id="ID19"), "Ok.")
        post = next(r for r in self.requests if r.method == "POST")
        self.assertEqual(json.loads(post.content), {"request": "triggerButton", "buttonID": "ID19"})
        self.assertEqual(post.headers["Authorization"], "secret")

    async def test_message_actions(self) -> None:
        actions = ActionRegistry()
        self._connection().add_actions(actions)
        await actions.run("sammi.popup", message="clip done")
        await actions.run("sammi.alert", message="careful")
        await actions.run("sammi.notification", message="30sec timer finished", title="Timer")
        posts = [json.loads(r.content) for r in self.requests if r.method == "POST"]
        self.assertEqual(posts, [{"request": "popupMessage", "message": "clip done"},
                                 {"request": "alertMessage", "message": "careful"},
                                 {"request": "notificationMessage", "title": "Timer",
                                  "message": "30sec timer finished"}])

    async def test_button_deck_and_variable_actions(self) -> None:
        actions = ActionRegistry()
        self._connection().add_actions(actions)
        await actions.run("sammi.release_button", button_id="ID19")
        await actions.run("sammi.set_deck", deck="2025", state="toggle")
        await actions.run("sammi.modify_button", button_id="ID19", text="Hi", color="#ff8800")
        await actions.run("sammi.modify_button", button_id="ID19")
        self.assertEqual(await actions.run("sammi.get_variable", name="count", button_id="ID19"), "x64")
        self.assertTrue(await actions.run("sammi.get_deck_on", deck="2025"))
        posts = [json.loads(r.content) for r in self.requests if r.method == "POST"]
        self.assertEqual(posts, [{"request": "releaseButton", "buttonID": "ID19"},
                                 {"request": "changeDeckStatus", "deckID": "2025", "status": 2},
                                 {"request": "modifyButton", "buttonID": "ID19", "text": "Hi", "color": 0x0088ff},
                                 {"request": "modifyButton", "buttonID": "ID19"}])
        gets = [str(r.url).split("?")[1] for r in self.requests
                if r.method == "GET" and "Architecture" not in str(r.url)]  # the start check aside
        self.assertEqual(gets, ["request=getVariable&name=count&buttonID=ID19", "request=getDeckStatus&deckID=2025"])
        with self.assertRaisesRegex(ValueError, "state must be"):
            await actions.run("sammi.set_deck", deck="2025", state="maybe")
        with self.assertRaisesRegex(ValueError, "#rrggbb"):
            await actions.run("sammi.modify_button", button_id="ID19", color="orange")

    async def test_button_dropdown_reads_the_decks_from_sammi(self) -> None:
        def sammi(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return httpx.Response(200, json={"data": [{"deckId": "1", "deckName": "stream", "status": 1,
                                                       "buttons": [{"id": "ID24", "text": "twitch_marker"}]}]})

        actions = ActionRegistry()
        SammiConnection({"enabled": True}, lambda: ("{}", 0), httpx.MockTransport(sammi)).add_actions(actions)
        choices = await actions.get("sammi.trigger_button").options["button_id"]()
        self.assertEqual(choices, {"stream": {"ID24": "twitch_marker  [ID24]"}})  # by deck
        self.assertEqual((await actions.get("sammi.set_variable").options["button_id"]())["(global)"],
                         {"global": "global (not a button)"})
        self.assertEqual(str(self.requests[0].url), "http://127.0.0.1:9450/api?request=getDeckList")
        self.assertEqual(await actions.run("sammi.get_decks"), [
            {"name": "stream", "id": "1", "enabled": True, "buttons": [{"id": "ID24", "text": "twitch_marker"}]}])

    async def test_switched_off_refuses(self) -> None:
        actions = ActionRegistry()
        self._connection(enabled=False).add_actions(actions)
        with self.assertRaises(NotConnectedError):
            await actions.run("sammi.set_variable", name="a", value="b")
        self.assertEqual(self.requests, [])


if __name__ == "__main__":
    unittest.main()
