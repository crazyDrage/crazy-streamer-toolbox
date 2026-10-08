import tempfile
import unittest
from pathlib import Path

import httpx

from streamer_toolbox.core.config.config_table_writer import ConfigTableWriter
from streamer_toolbox.core.widgets.streamelements_fallback import StreamElementsFallback


class TestStreamElementsFallback(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.asked: list[str] = []

    def _answer(self, request: httpx.Request) -> httpx.Response:
        self.asked.append(str(request.url))
        if request.url.path.endswith("/channels/kit"):
            return httpx.Response(200, json={"_id": "se2", "provider": "twitch"})
        return httpx.Response(404, json={"error": "Not Found"})

    async def test_off_at_the_start_streamelements_is_never_asked(self) -> None:
        fallback = StreamElementsFallback({}, transport=httpx.MockTransport(self._answer))
        self.assertFalse(fallback.on)
        self.assertIsNone(await fallback.get("channels/kit"))
        self.assertEqual(self.asked, [])

    async def test_on_it_hands_on_what_streamelements_says(self) -> None:
        fallback = StreamElementsFallback({"streamelements_fallback": True},
                                          transport=httpx.MockTransport(self._answer))
        self.assertEqual(await fallback.get("channels/kit"), {"_id": "se2", "provider": "twitch"})
        self.assertIsNone(await fallback.get("channels/nobody"))  # they say no
        self.assertEqual(self.asked, ["https://api.streamelements.com/kappa/v2/channels/kit",
                                      "https://api.streamelements.com/kappa/v2/channels/nobody"])

        def down(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("no StreamElements any more")
        gone = StreamElementsFallback({"streamelements_fallback": True}, transport=httpx.MockTransport(down))
        self.assertIsNone(await gone.get("channels/kit"))

    async def test_the_switch_is_kept_in_the_settings_file(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "toolbox.toml"
            fallback = StreamElementsFallback({}, ConfigTableWriter(path))
            fallback.set(True)
            self.assertTrue(fallback.on)
            self.assertIn("[widgets]\nstreamelements_fallback = true", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
