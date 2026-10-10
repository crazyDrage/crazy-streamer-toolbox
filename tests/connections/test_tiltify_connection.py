import asyncio
import tempfile
import time
import unittest
from pathlib import Path
from urllib.parse import parse_qs

import httpx

from streamer_toolbox.connections.tiltify.tiltify_feed import TiltifyFeed, tiltify_donation
from streamer_toolbox.connections.tiltify_connection import TiltifyConnection
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.events.event_fields import EVENT_FIELDS

SECRET = "tiltify-secret"
DONATION = {"id": "d-1", "amount": {"currency": "USD", "value": "25.00"}, "campaign_id": "c-1",
            "completed_at": "2999-01-01T10:00:00Z", "donor_name": "ann", "donor_comment": "for the lizards"}


async def until(check, timeout: float = 3.0) -> None:
    end = time.monotonic() + timeout
    while not check():
        if time.monotonic() > end:
            raise AssertionError("timed out")
        await asyncio.sleep(0.02)


class TestTiltifyConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.secret = Path(self._dir.name) / "tiltify_secret.txt"
        self.secret.write_text(SECRET, encoding="utf-8")
        self.events = EventBus()
        self.seen: list[tuple[str, dict]] = []
        self.donations: list[dict] = []
        self.logins = 0
        self.token = "t-1"
        self.asked: list[dict] = []

        async def listen(kind: str, data: dict) -> None:
            self.seen.append((kind, data))

        self.events.subscribe(listen)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _tiltify(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth/token":
            form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
            if (form["client_id"], form["client_secret"]) != ("app", SECRET):
                return httpx.Response(401, json={"error": "invalid_client"})
            self.logins += 1
            return httpx.Response(200, json={"access_token": self.token, "expires_in": 7200})
        if request.headers.get("authorization") != f"Bearer {self.token}":
            return httpx.Response(401, json={"error": "expired"})
        if request.url.path == "/api/public/campaigns/by/slugs/drage/lizards":
            return httpx.Response(200, json={"data": {"id": "c-1", "name": "Lizard rescue"}})
        if request.url.path == "/api/public/campaigns/c-1/donations":
            self.asked.append(dict(request.url.params))
            return httpx.Response(200, json={"data": list(self.donations), "metadata": {}})
        return httpx.Response(404, json={"error": "not found"})

    def _connection(self, **settings) -> TiltifyConnection:
        return TiltifyConnection({"enabled": True, "client_id": "app", "user": "@drage", "campaign": "lizards",
                                  **settings}, self.secret, self.events, httpx.MockTransport(self._tiltify))

    def test_a_donation_becomes_the_toolbox_event(self) -> None:
        event = tiltify_donation(DONATION, "Lizard rescue")
        self.assertEqual(event, {"user": "ann", "amount": 25.0, "currency": "USD", "message": "for the lizards",
                                 "campaign": "Lizard rescue", "platform": "tiltify"})
        self.assertEqual(set(event), set(EVENT_FIELDS["tiltify.donation"]))
        self.assertEqual(tiltify_donation({"id": "x"}, "")["user"], "Anonymous")

    async def test_connect_looks_the_campaign_up_and_says_what_is_missing_or_wrong(self) -> None:
        tried = await self._connection().test(self._connection().settings)
        self.assertEqual((tried.state, tried.facts), (ConnectionState.CONNECTED, (("Campaign", "Lizard rescue"),)))
        missing = self._connection(user="", campaign="")
        self.assertEqual((await missing.test(missing.settings)).detail, "Not set yet: user, campaign")
        unknown = self._connection(campaign="snakes")
        self.assertIn("knows no campaign drage/snakes", (await unknown.test(unknown.settings)).detail)
        self.secret.write_text("wrong", encoding="utf-8")
        refused = self._connection()
        detail = (await refused.test(refused.settings)).detail
        self.assertIn("refused the application", detail)
        self.assertNotIn("wrong", detail.replace("wrong one", ""))
        self.secret.write_text("", encoding="utf-8")
        await refused.start()
        self.assertIn("No client secret yet", refused.status.detail)

    async def test_each_new_donation_is_told_once_and_a_run_out_token_is_renewed(self) -> None:
        async def on_event(data: dict) -> None:
            self.events.publish("tiltify.donation", data)

        states: list[str] = []
        feed = TiltifyFeed("app", SECRET, "drage", "lizards", on_event, states.append, 0.02,
                           httpx.MockTransport(self._tiltify))
        task = asyncio.create_task(feed.run())
        await until(lambda: len(self.asked) >= 2)
        self.assertEqual(self.seen, [])
        self.assertEqual(states[0], "listening")
        self.assertEqual(self.asked[0]["limit"], "100")
        self.donations.append(DONATION)
        await until(lambda: len(self.seen) == 1)
        self.assertEqual(self.seen[0][1]["user"], "ann")
        self.token = "t-2"  # the old token stops working
        self.donations.append({**DONATION, "id": "d-2", "donor_name": "bob", "completed_at": "2999-01-01T11:00:00Z"})
        await until(lambda: len(self.seen) == 2)
        self.assertEqual((self.logins, self.seen[1][1]["user"]), (2, "bob"))
        await until(lambda: self.asked[-1]["completed_after"] == "2999-01-01T11:00:00Z")  # only what is newer
        await asyncio.sleep(0.1)
        self.assertEqual(len(self.seen), 2)  # still listed by Tiltify, not told again
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def test_the_connection_listens_and_stops(self) -> None:
        connection = self._connection()
        await connection.start()
        await until(lambda: connection.status.state is ConnectionState.CONNECTED)
        self.assertEqual(connection.status.facts, (("Feed", "donations"),))
        await connection.stop()
        self.assertEqual(connection.status.state, ConnectionState.OFF)
        self.assertFalse(TiltifyConnection({}, self.secret, self.events).settings["enabled"])


if __name__ == "__main__":
    unittest.main()
