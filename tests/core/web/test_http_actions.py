import json
import unittest

import httpx

from streamer_toolbox.core.web.http_actions import HttpActions


class TestHttpActions(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.requests: list[httpx.Request] = []

    def _board(self, request: httpx.Request) -> httpx.Response:
        """Answers like the vibration board: /status lists the outputs, /relay/<id> switches one."""
        self.requests.append(request)
        if request.url.path == "/status":
            return httpx.Response(200, json={"result": [{"id": 0, "mode": "switch", "on": False}]})
        if request.url.path.startswith("/relay/"):
            return httpx.Response(200, text="OK")
        return httpx.Response(404, text="no such page")

    def _http(self) -> HttpActions:
        return HttpActions(httpx.MockTransport(self._board))

    async def test_get_reads_json(self) -> None:
        answer = await self._http().request("http://board/status")
        self.assertEqual(answer, {"status": 200, "ok": True,
                                  "body": {"result": [{"id": 0, "mode": "switch", "on": False}]}})

    async def test_post_with_query_body_and_headers(self) -> None:
        answer = await self._http().request("http://board/relay/0", "post", query={"turn": "on"},
                                            body={"brightness": 50}, headers='{"X-Key": "k"}')
        sent = self.requests[0]
        self.assertEqual((answer["body"], sent.method, str(sent.url)), ("OK", "POST", "http://board/relay/0?turn=on"))
        self.assertEqual(json.loads(sent.content), {"brightness": 50})
        self.assertEqual((sent.headers["Content-Type"], sent.headers["X-Key"]), ("application/json", "k"))

    async def test_query_as_text(self) -> None:
        await self._http().request("http://board/relay/1", "POST", query="?turn=off&x=1")
        self.assertEqual(str(self.requests[0].url), "http://board/relay/1?turn=off&x=1")

    async def test_errors(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "answered 404"):
            await self._http().request("http://board/nothing")
        answer = await self._http().request("http://board/nothing", fail_on_error="false")
        self.assertEqual((answer["status"], answer["ok"]), (404, False))
        with self.assertRaisesRegex(ValueError, "http://"):
            await self._http().request("board/status")
        with self.assertRaisesRegex(ValueError, "method"):
            await self._http().request("http://board/status", "FETCH")

    async def test_unreachable(self) -> None:
        def down(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused", request=request)

        with self.assertRaisesRegex(ConnectionError, "can't reach"):
            await HttpActions(httpx.MockTransport(down)).request("http://board/status")


if __name__ == "__main__":
    unittest.main()
