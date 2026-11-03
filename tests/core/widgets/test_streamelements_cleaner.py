import tempfile
import unittest
from pathlib import Path

import httpx

from streamer_toolbox.core.widgets.streamelements_cleaner import StreamElementsCleaner
from streamer_toolbox.core.widgets.streamelements_media import StreamElementsMedia
from streamer_toolbox.core.widgets.widget import Widget
from streamer_toolbox.core.widgets.widget_helpers import WidgetHelpers
from streamer_toolbox.core.widgets.widget_store import WidgetStore

HTML = '<script src="https://example.org/lib.js"></script><img src="https://cdn.streamelements.com/uploads/a.png">'
JS = 'fetch("https://api.streamelements.com/kappa/v2/channels/me");'
VALUES = {"sound": "https://cdn.streamelements.com/uploads/gone.mp3", "size": 12}


class TestStreamElementsCleaner(unittest.IsolatedAsyncioTestCase):
    """His round 64: "clean out StreamElements" writes the links and the files into the widget itself."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.store = WidgetStore(Path(self._dir.name))
        self.store.save(Widget("alert", HTML, "", JS, {"sound": {"type": "sound-input"}}, VALUES))

        def server(request: httpx.Request) -> httpx.Response:
            if "gone" in request.url.path:
                return httpx.Response(404)
            return httpx.Response(200, content=b"bytes")

        transport = httpx.MockTransport(server)
        self.cleaner = StreamElementsCleaner(self.store, StreamElementsMedia(self.store, transport),
                                             WidgetHelpers(self.store, transport))

    def tearDown(self) -> None:
        self._dir.cleanup()

    async def test_links_point_at_the_toolbox_and_the_files_are_kept(self) -> None:
        changed, missed = await self.cleaner.clean("alert")
        self.assertEqual(changed, 3)  # the picture, the API question and the sound in the values
        self.assertEqual(missed, ["https://cdn.streamelements.com/uploads/gone.mp3"])
        widget = self.store.get("alert")
        self.assertNotIn("streamelements.com", widget.html + widget.js + str(widget.values))
        self.assertIn("/overlay/streamelements/api/kappa/v2/channels/me", widget.js)
        self.assertEqual(widget.values["size"], 12)
        self.assertIn("cdn/uploads/a.png", self.store.streamelements_media("alert"))
        self.assertTrue(self.store.helpers("alert"))  # the helper script is kept too

    async def test_a_clean_widget_stays_as_it_is(self) -> None:
        self.store.save(Widget("plain", "<p>hi</p>"))
        self.assertEqual(await self.cleaner.clean("plain"), (0, []))
        with self.assertRaises(KeyError):
            await self.cleaner.clean("missing")
