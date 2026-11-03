import unittest

import httpx

from streamer_toolbox.core.web.web_error import web_error


class TestWebError(unittest.TestCase):
    def test_a_failed_request_in_a_few_words(self) -> None:
        request = httpx.Request("GET", "https://example.com/listing.json")
        missing = httpx.HTTPStatusError("long text", request=request, response=httpx.Response(404, request=request))
        self.assertEqual(web_error(missing), "404 Not Found")
        self.assertEqual(web_error(httpx.ConnectError("getaddrinfo failed")), "no connection (getaddrinfo failed)")
        self.assertEqual(web_error(httpx.ReadTimeout("")), "no answer in time")


if __name__ == "__main__":
    unittest.main()
