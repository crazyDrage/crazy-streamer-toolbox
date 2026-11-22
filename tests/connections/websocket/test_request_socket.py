import asyncio
import time
import unittest

from streamer_toolbox.connections.websocket.answer_lost_error import AnswerLostError
from streamer_toolbox.connections.websocket.request_socket import RequestSocket
from tests.fakes.fake_json_socket_server import FakeJsonSocketServer


async def until(check, timeout: float = 3.0) -> None:
    end = time.monotonic() + timeout
    while not check():
        if time.monotonic() > end:
            raise AssertionError("timed out")
        await asyncio.sleep(0.02)


def echo(message: dict, path: str) -> dict | None:
    """Answers every message that has a "ref" with the same ref; says nothing to the rest, nor to a "quiet" one."""
    if "ref" not in message or message.get("quiet"):
        return None
    return {"ref": message["ref"], "you_said": message.get("say")}


class TestRequestSocket(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.states: list[str] = []
        self.told: list[dict] = []

    async def _told(self, message: dict) -> None:
        self.told.append(message)

    async def _run(self, line: RequestSocket) -> asyncio.Task:
        task = asyncio.create_task(line.run())
        self.addAsyncCleanup(self._stop, task)
        return task

    @staticmethod
    async def _stop(task: asyncio.Task) -> None:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def test_a_request_gets_its_own_answer_and_other_messages_are_handed_on(self) -> None:
        async with FakeJsonSocketServer(echo) as server:
            line = RequestSocket("Program", lambda: server.url, self._told, on_state=self.states.append,
                                 id_key="ref", retry_delay=0.05, timeout=0.3)
            with self.assertRaisesRegex(ConnectionError, "Program is not connected"):
                await line.request({"say": "early"})
            await self._run(line)
            await until(lambda: self.states == ["connected"])
            first, second = await asyncio.gather(line.request({"say": "a"}), line.request({"say": "b"}))
            self.assertEqual((first["you_said"], second["you_said"]), ("a", "b"))
            await server.tell({"event": "something happened"})
            await until(lambda: self.told == [{"event": "something happened"}])
            await line.send({"say": "no answer wanted"})
            await until(lambda: server.received[-1] == {"say": "no answer wanted"})
            with self.assertRaisesRegex(TimeoutError, "Program didn't answer"):
                await line.request({"say": "x", "quiet": True}, timeout=0.05)

    async def test_it_connects_again_and_a_refused_key_stops_it(self) -> None:
        opened: list[int] = []
        refuse = False

        async def on_open(line: RequestSocket) -> None:
            opened.append(1)
            if refuse:
                raise PermissionError("the key secret-1 was refused")
            await line.request({"say": "hello"})

        async with FakeJsonSocketServer(echo) as server:
            url = server.url
            line = RequestSocket("Program", lambda: url, on_open=on_open, on_state=self.states.append,
                                 id_key="ref", retry_delay=0.05, beat=(0.05, {"keep": "alive"}),
                                 hide=lambda text: text.replace("secret-1", "<key>"))
            task = await self._run(line)
            await until(lambda: self.states == ["connected"])
            await until(lambda: server.received.count({"keep": "alive"}) >= 2)
        await until(lambda: len(self.states) >= 2)
        self.assertIn("trying again", self.states[1])
        self.assertFalse(line.connected)
        async with FakeJsonSocketServer(echo) as again:
            url = again.url
            await until(lambda: self.states[-1] == "connected")
            self.assertEqual(len(opened), 2)
        refuse = True
        async with FakeJsonSocketServer(echo) as last:
            url = last.url
            await until(lambda: task.done())
        self.assertEqual(self.states[-1], "the key <key> was refused")

    async def test_a_dropped_line_comes_back_at_once_without_telling_an_error(self) -> None:
        async with FakeJsonSocketServer(echo) as server:
            line = RequestSocket("Program", lambda: server.url, on_state=self.states.append, id_key="ref",
                                 retry_delay=5, again_after=0.01)
            await self._run(line)
            await until(lambda: self.states == ["connected"])
            await server.drop()
            await until(lambda: self.states == ["connected", "connected"])
            self.assertEqual((await line.request({"say": "back"}))["you_said"], "back")

    async def test_reopen_waits_for_the_line_and_says_when_it_does_not_come_back(self) -> None:
        async with FakeJsonSocketServer(echo) as server:
            url = server.url
            line = RequestSocket("Program", lambda: url, on_state=self.states.append, id_key="ref",
                                 retry_delay=5, again_after=0.01, timeout=0.3)
            await self._run(line)
            await until(lambda: self.states == ["connected"])
            await line.reopen()
            self.assertEqual(self.states, ["connected", "connected"])
            self.assertEqual(len(server.paths), 2)
        with self.assertRaisesRegex(ConnectionError, "Program"):
            await line.reopen()
        self.assertIn("trying again in 5 s", self.states[-1])

    async def test_an_answer_lost_with_the_line_is_said_as_such(self) -> None:
        async with FakeJsonSocketServer(echo) as server:
            line = RequestSocket("Program", lambda: server.url, on_state=self.states.append, id_key="ref",
                                 retry_delay=5, again_after=0.01, timeout=2)
            await self._run(line)
            await until(lambda: self.states == ["connected"])
            waiting = asyncio.create_task(line.request({"say": "x", "quiet": True}))
            await until(lambda: len(server.received) == 1)
            await server.drop()
            with self.assertRaisesRegex(AnswerLostError, "closed the line before it answered"):
                await waiting


if __name__ == "__main__":
    unittest.main()
