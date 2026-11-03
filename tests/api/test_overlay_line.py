import asyncio
import unittest

from streamer_toolbox.api import overlay_line
from tests.fakes.fake_overlay_socket import FakeOverlaySocket

ALERT = {"type": "alert", "alert": {"text": "Kit followed"}}


class TestOverlayLine(unittest.IsolatedAsyncioTestCase):
    """His round 64: the toolbox should know when an alert or event didn't reach the page in OBS."""

    def setUp(self) -> None:
        self.inbox: asyncio.Queue = asyncio.Queue()
        self.missed: list[dict] = []

    def _serve(self, socket: FakeOverlaySocket, heartbeat: float = 10.0) -> asyncio.Task:
        return asyncio.create_task(overlay_line.serve(socket, self.inbox, heartbeat, self.missed.append,
                                                      ack_wait=0.2))

    async def _sent(self, socket: FakeOverlaySocket, count: int) -> None:
        for _ in range(200):
            if len(socket.sent) >= count:
                return
            await asyncio.sleep(0.01)
        self.fail(f"only {len(socket.sent)} sent")

    async def test_a_page_that_answers_keeps_its_line_and_nothing_is_missed(self) -> None:
        socket = FakeOverlaySocket({"ack": "1"})
        line = self._serve(socket)
        self.inbox.put_nowait(ALERT)
        await self._sent(socket, 1)
        self.assertEqual(socket.sent[0], {**ALERT, "n": 1})
        socket.say({"type": "got", "n": 1})
        await asyncio.sleep(0.4)  # longer than ack_wait
        self.assertFalse(line.done())
        socket.leave()
        await line
        self.assertEqual(self.missed, [])

    async def test_an_alert_without_an_answer_ends_the_line_and_is_missed(self) -> None:
        socket = FakeOverlaySocket({"ack": "1"})
        line = self._serve(socket)
        self.inbox.put_nowait(ALERT)
        await asyncio.wait_for(line, 2)
        self.assertTrue(socket.closed)
        self.assertEqual(self.missed, [ALERT])

    async def test_an_unanswered_alive_finds_a_gone_page_without_any_alert(self) -> None:
        socket = FakeOverlaySocket({"ack": "1"})
        await asyncio.wait_for(self._serve(socket, heartbeat=0.05), 2)
        self.assertEqual(socket.sent[0], {"type": "alive", "n": 1})
        self.assertTrue(socket.closed)
        self.assertEqual(self.missed, [])  # "alive" isn't news he missed

    async def test_what_was_still_waiting_to_be_sent_is_missed_too(self) -> None:
        socket = FakeOverlaySocket({"ack": "1"})
        line = self._serve(socket)
        await asyncio.sleep(0.05)
        socket.leave()
        self.inbox.put_nowait(ALERT)
        await line
        self.assertEqual(self.missed, [ALERT])

    async def test_what_a_page_confirms_goes_to_arrived(self) -> None:
        socket, arrived = FakeOverlaySocket({"ack": "1"}), []
        line = asyncio.create_task(overlay_line.serve(socket, self.inbox, 10.0, self.missed.append, 0.2,
                                                      arrived.append))
        self.inbox.put_nowait(ALERT)
        await self._sent(socket, 1)
        socket.say({"type": "got", "n": 1})
        socket.leave()
        await line
        self.assertEqual((arrived, self.missed), ([ALERT], []))

    def test_resume_reads_the_run_and_the_last_id(self) -> None:
        self.assertEqual(overlay_line.resume(FakeOverlaySocket({"run": "ab12", "after": "57"})), ("ab12", 57))
        self.assertEqual(overlay_line.resume(FakeOverlaySocket({"after": "x"})), (None, None))

    async def test_a_page_that_doesnt_answer_gets_plain_messages(self) -> None:
        """A page from before ?ack=1 (OBS may keep an old one): no numbers, its line isn't ended for silence."""
        socket = FakeOverlaySocket()
        line = self._serve(socket)
        self.inbox.put_nowait(ALERT)
        await asyncio.sleep(0.4)
        self.assertEqual(socket.sent, [ALERT])
        self.assertFalse(line.done())
        socket.leave()
        await line
        self.assertEqual(self.missed, [])


if __name__ == "__main__":
    unittest.main()
