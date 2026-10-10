import unittest

import httpx

from streamer_toolbox.core.web.web_client import shared_ssl_context, web_client


class TestWebClient(unittest.IsolatedAsyncioTestCase):
    async def test_every_client_shares_one_ssl_context(self) -> None:
        self.assertIs(shared_ssl_context(), shared_ssl_context())
        contexts = []
        for _ in range(2):
            async with web_client(timeout=5) as client:
                contexts.append(client._transport._pool._ssl_context)  # httpx has no public way to ask
        self.assertIs(contexts[0], contexts[1])
        self.assertIs(contexts[0], shared_ssl_context())

    async def test_a_given_transport_is_used_as_it_is(self) -> None:
        asked = []

        def answer(request: httpx.Request) -> httpx.Response:
            asked.append(str(request.url))
            return httpx.Response(200, json={"ok": True})

        async with web_client(httpx.MockTransport(answer), timeout=5, base_url="https://api.test") as client:
            self.assertEqual((await client.get("/x")).json(), {"ok": True})
        self.assertEqual(asked, ["https://api.test/x"])


if __name__ == "__main__":
    unittest.main()
