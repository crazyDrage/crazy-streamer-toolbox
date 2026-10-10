import tempfile
import unittest
from pathlib import Path

import httpx

from streamer_toolbox.core.history.event_history import EventHistory
from streamer_toolbox.core.widgets.streamelements_import import StreamElementsImport
from streamer_toolbox.core.widgets.streamelements_session import StreamElementsSession
from streamer_toolbox.core.widgets.widget_session import WidgetSession

# the shape of StreamElements' real answer (2026-10-04), names changed
ANSWER = {"_id": "s1", "channel": "acc1", "data": {
    "follower-latest": {"name": "se_follower"},
    "subscriber-latest": {"name": "ann", "amount": 1, "tier": "1000", "message": ""},
    "subscriber-recent": [{"name": "ann", "tier": "1000", "amount": 1, "createdAt": "2026-09-09T18:58:12.969Z"},
                          {"name": "bob", "tier": "1000", "amount": 1, "createdAt": "2026-08-15T15:35:11.770Z"}],
    "cheer-latest": {"name": "cy", "amount": 1, "message": "Cheer1 hi"},
    "cheer-total": {"amount": 1101}, "cheer-count": {"count": 40},
    "cheer-alltime-top-donator": {"name": "cy", "amount": 600},
    "raid-latest": {"name": "dee", "amount": 10},
    "tip-latest": {"name": "", "amount": 0},
    "host-latest": {"name": "", "amount": 0}}}


class TestStreamElementsSession(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.token = Path(self._dir.name) / "streamelements_token.txt"
        self.asked: list[httpx.Request] = []
        self.status = 200

        def streamelements(request: httpx.Request) -> httpx.Response:
            self.asked.append(request)
            return httpx.Response(self.status, json=ANSWER)

        self.bringer = StreamElementsSession(StreamElementsImport(self.token), httpx.MockTransport(streamelements))

    def tearDown(self) -> None:
        self._dir.cleanup()

    async def test_fills_what_the_toolbox_doesnt_know_and_leaves_what_it_saw(self) -> None:
        self.token.write_text("jwt-token\nacc1\n", encoding="utf-8")
        session = WidgetSession(Path(self._dir.name) / "session.json")
        session.add("follower-latest", {"type": "follower", "name": "seen_by_toolbox"})
        self.assertEqual(await self.bringer.bring(session), ["subscriber", "cheer", "raid"])
        self.assertEqual(str(self.asked[0].url), "https://api.streamelements.com/kappa/v2/sessions/acc1")
        self.assertEqual(self.asked[0].headers["authorization"], "Bearer jwt-token")
        self.assertEqual(session.data["follower-latest"]["name"], "seen_by_toolbox")  # its own stays
        self.assertEqual(session.data["subscriber-latest"], {
            "amount": 1, "message": "", "name": "ann", "tier": "1000", "createdAt": "2026-09-09T18:58:12.969Z",
            "type": "subscriber"})
        self.assertEqual([one["name"] for one in session.data["subscriber-recent"]], ["ann", "bob"])
        self.assertEqual(session.data["cheer-latest"]["message"], "Cheer1 hi")
        self.assertEqual((session.data["raid-latest"]["amount"], session.data["tip-latest"]["name"]), (10, ""))
        self.assertEqual(session.data["subscriber-session"]["count"], 0)  # nothing happened in this session
        # kept: there again after a restart, and a second press changes nothing
        again = WidgetSession(Path(self._dir.name) / "session.json")
        self.assertEqual(again.data["subscriber-latest"]["name"], "ann")
        self.assertEqual(await self.bringer.bring(again), [])

    async def test_the_past_moves_into_the_toolboxes_own_record_once(self) -> None:
        self.token.write_text("jwt-token\nacc1\n", encoding="utf-8")
        history = EventHistory(Path(self._dir.name) / "events.jsonl")
        bringer = StreamElementsSession(StreamElementsImport(self.token), self.bringer._transport, history)
        session = WidgetSession(history=history)
        self.assertEqual(await bringer.bring(session), ["follower", "subscriber", "cheer", "raid"])
        self.assertEqual(session.data["cheer-total"], {"count": 40, "amount": 1101})
        self.assertEqual(session.data["cheer-alltime-top-donator"], {"name": "cy", "amount": 600})
        session.add("cheer-latest", {"type": "cheer", "name": "cy", "amount": 9})  # a new one counts on top
        self.assertEqual((session.data["cheer-total"], session.data["cheer-session-top-donator"]),
                         ({"count": 41, "amount": 1110}, {"name": "cy", "amount": 9}))
        self.assertEqual(await bringer.bring(session), [])  # pressing again adds nothing twice
        self.assertEqual(session.data["cheer-total"]["amount"], 1110)

    async def test_without_a_token_or_with_a_refused_one_it_says_so(self) -> None:
        session = WidgetSession()
        with self.assertRaises(PermissionError):
            await self.bringer.bring(session)
        self.token.write_text("old\nacc1", encoding="utf-8")
        self.status = 401
        with self.assertRaises(PermissionError):
            await self.bringer.bring(session)
        self.assertEqual(session.data["subscriber-latest"]["name"], "")


if __name__ == "__main__":
    unittest.main()
