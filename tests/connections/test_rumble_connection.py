import asyncio
import copy
import tempfile
import unittest
from pathlib import Path

import httpx

from streamer_toolbox.connections.rumble.rumble_news import RumbleNews
from streamer_toolbox.connections.rumble_connection import RumbleConnection
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.events.event_fields import EVENT_FIELDS

ADDRESS = "https://rumble.com/-livestream-api/get-data?key=secret-key"
# the shape of Rumble's documented example answer, shortened
ANSWER = {
    "now": 1700000000, "type": "user", "user_id": "_u1", "channel_id": None, "since": None, "max_num_results": 50,
    "followers": {"num_followers": 2, "num_followers_total": 12, "latest_follower": {"username": "ann"},
                  "recent_followers": [{"username": "ann", "followed_on": "2026-10-04T10:00:00+00:00"}]},
    "subscribers": {"num_subscribers": 0, "latest_subscriber": None, "recent_subscribers": []},
    "gifted_subs": {"num_gifted_subs": 0, "latest_gifted_sub": None, "recent_gifted_subs": []},
    "livestreams": [{"id": "s1", "title": "Lizards", "created_on": "2026-10-04T09:00:00+00:00", "is_live": True,
                     "categories": {}, "stream_key": "never-shown", "likes": 1, "dislikes": 0, "watching_now": 3,
                     "chat": {"latest_message": None, "recent_messages": [
                         {"username": "ann", "badges": [], "text": "hi", "created_on": "2026-10-04T10:00:01+00:00"}],
                         "latest_rant": None, "recent_rants": []}}],
}


def later() -> dict:
    """The next answer: a new follower, a sub, gifted subs, two chat messages and a rant; the old ones still there."""
    answer = copy.deepcopy(ANSWER)
    answer["followers"]["recent_followers"].insert(0, {"username": "bob", "followed_on": "2026-10-04T10:05:00+00:00"})
    answer["subscribers"]["recent_subscribers"] = [{"username": "cy", "user": "cy", "amount_cents": 500,
                                                    "amount_dollars": 5, "subscribed_on": "2026-10-04T10:06:00+00:00"}]
    answer["gifted_subs"]["recent_gifted_subs"] = [{"total_gifts": 3, "remaining_gifts": 3, "purchased_by": "dee"}]
    chat = answer["livestreams"][0]["chat"]
    chat["recent_messages"] = [
        {"username": "mo", "badges": ["premium", "moderator"], "text": "!lizard two  times",
         "created_on": "2026-10-04T10:07:02+00:00"},
        {"username": "ann", "badges": [], "text": "hi", "created_on": "2026-10-04T10:07:00+00:00"},  # same words, later
    ] + chat["recent_messages"]
    chat["recent_rants"] = [{"username": "eve", "badges": [], "text": "for snacks", "amount_cents": 250,
                             "amount_dollars": 2.5, "created_on": "2026-10-04T10:08:00+00:00",
                             "expires_on": "2026-10-04T10:10:00+00:00"}]
    return answer


class TestRumbleConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.address = Path(self._dir.name) / "rumble_address.txt"
        self.events = EventBus()
        self.seen: list[tuple[str, dict]] = []
        self.asked: list[str] = []
        self.answers: list = [ANSWER]

        async def listen(kind: str, data: dict) -> None:
            self.seen.append((kind, data))

        self.events.subscribe(listen)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _connection(self, seconds: float = 2) -> RumbleConnection:
        def rumble(request: httpx.Request) -> httpx.Response:
            self.asked.append(str(request.url))
            answer = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
            return answer if isinstance(answer, httpx.Response) else httpx.Response(200, json=answer)

        return RumbleConnection({"enabled": True, "seconds": seconds}, self.address, self.events,
                                transport=httpx.MockTransport(rumble))

    def test_the_first_answer_is_no_news_and_later_ones_only_what_is_new(self) -> None:
        news = RumbleNews()
        self.assertEqual(news.news(ANSWER), [])  # what was there before the toolbox listened
        self.assertEqual(news.news(ANSWER), [])
        events = news.news(later())
        self.assertEqual(events, [
            ("rumble.follow", {"user": "bob", "followed_at": "2026-10-04T10:05:00+00:00", "platform": "rumble"}),
            ("rumble.sub", {"user": "cy", "amount": 5, "platform": "rumble"}),
            ("rumble.gift", {"user": "dee", "amount": 3, "platform": "rumble"}),
            ("rumble.chat", {"user": "ann", "message": "hi", "command": "", "args": "", "role": "viewer",
                             "platform": "rumble"}),  # the same words again, at a later time: a new message
            ("rumble.chat", {"user": "mo", "message": "!lizard two  times", "command": "!lizard",
                             "args": "two  times", "role": "mod", "platform": "rumble"}),
            ("rumble.rant", {"user": "eve", "amount": 2.5, "message": "for snacks", "platform": "rumble"}),
            ("tip", {"user": "eve", "amount": 2.5, "currency": "USD", "message": "for snacks", "platform": "rumble"}),
        ])
        for kind, data in events:
            # what the Start box offers is what comes; role: the event bus adds it (RoleBook)
            self.assertEqual(set(data) - {"role"}, set(EVENT_FIELDS[kind]) - {"role"})
        self.assertEqual(news.news(later()), [])  # told once

    def test_going_live_and_ending(self) -> None:
        news = RumbleNews()
        off = copy.deepcopy(ANSWER)
        off["livestreams"] = []
        self.assertEqual(news.news(off), [])
        live = news.news(ANSWER)  # the chat that comes with the stream, then that it is live
        self.assertEqual([kind for kind, _ in live], ["rumble.chat", "rumble.online"])
        self.assertEqual(live[-1][1], {"title": "Lizards", "platform": "rumble"})
        self.assertEqual(news.news(off), [("rumble.offline", {"title": "Lizards", "platform": "rumble"})])
        self.assertEqual(news.news({"livestreams": "broken", "followers": None}), [])  # an odd answer is no news

    async def test_it_is_off_until_switched_on_and_needs_the_address_file(self) -> None:
        self.assertFalse(RumbleConnection({}, self.address, self.events).settings["enabled"])
        connection = self._connection()
        await connection.start()
        self.assertEqual(connection.status.state, ConnectionState.ERROR)
        self.assertIn("No address yet", connection.status.detail)
        self.address.write_text("https://rumble.example.com/get-data?key=secret-key", encoding="utf-8")
        await connection.start()  # not Rumble's host: the key is never sent there
        self.assertIn("https://rumble.com/", connection.status.detail)
        self.assertNotIn("secret-key", connection.status.detail)
        self.assertEqual(self.asked, [])

    async def test_asks_again_and_again_and_passes_the_news_on(self) -> None:
        self.address.write_text(ADDRESS + "\n", encoding="utf-8")
        self.answers = [ANSWER, later()]
        connection = self._connection()
        connection._every = lambda: 0.05  # the test doesn't wait Rumble's seconds
        await connection.start()
        await asyncio.sleep(0.4)
        await self.events.wait_idle()
        self.assertEqual(connection.status.state, ConnectionState.CONNECTED)
        self.assertGreaterEqual(len(self.asked), 3)
        self.assertEqual(set(self.asked), {ADDRESS})
        self.assertEqual([kind for kind, _ in self.seen], ["rumble.follow", "rumble.sub", "rumble.gift", "rumble.chat",
                                                           "rumble.chat", "rumble.rant", "tip"])
        await connection.stop()
        self.assertEqual(connection.status.state, ConnectionState.OFF)

    async def test_a_refused_address_shows_on_the_tab_and_isnt_asked_again(self) -> None:
        self.address.write_text(ADDRESS, encoding="utf-8")
        self.answers = [httpx.Response(403, text="no")]
        connection = self._connection()
        tried = await connection.test({})
        self.assertEqual(tried.state, ConnectionState.ERROR)
        self.assertIn("refused the address", tried.detail)
        connection._every = lambda: 0.05
        await connection.start()
        await asyncio.sleep(0.3)
        self.assertEqual(connection.status.state, ConnectionState.ERROR)
        self.assertNotIn("secret-key", connection.status.detail)
        self.assertEqual(len(self.asked), 2)  # the test and one start: no asking in a loop
        await connection.stop()

    async def test_the_test_button_and_how_often_it_asks(self) -> None:
        self.address.write_text(ADDRESS, encoding="utf-8")
        tried = await self._connection().test({})
        self.assertEqual((tried.state, tried.facts), (ConnectionState.CONNECTED, (("Followers", "12"),)))
        self.assertEqual(self._connection(seconds=0.1)._every(), 2.0)  # never faster than that
        self.assertEqual(self._connection(seconds="soon")._every(), 5.0)
        self.assertEqual([field.key for field in self._connection().fields()], ["seconds"])


if __name__ == "__main__":
    unittest.main()
