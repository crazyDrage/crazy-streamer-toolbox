import tempfile
import unittest
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from streamer_toolbox.api.widget_router import build_widget_router
from streamer_toolbox.core.widgets.streamelements_media import StreamElementsMedia
from streamer_toolbox.core.widgets.widget import Widget
from streamer_toolbox.core.widgets.widget_hub import WidgetHub
from streamer_toolbox.core.widgets.widget_page import WidgetPage
from streamer_toolbox.core.widgets.widget_session import WidgetSession
from streamer_toolbox.core.widgets.widget_store import WidgetStore

HTML = """<img src="https://cdn.streamelements.com/uploads/lizard.png?v=2">
<video src="//cdn.streamelements.com/static/theme/Intro.WEBM"></video>
<img src="/overlay/streamelements/cdn/uploads/removed_link.gif">"""
JS = """fetch("https://api.streamelements.com/kappa/v2/channels/me");
const page = "https://streamelements.com/dashboard";
const gone = "https://cdn.streamelements.com/uploads/gone.mp3";"""
VALUES = {"alertSound": "https://cdn.streamelements.com/uploads/ding.ogg", "title": "hello", "size": 12}


class TestStreamElementsMedia(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.store = WidgetStore(Path(self._dir.name))
        fields = {"alertSound": {"type": "sound-input", "label": "Sound"}, "title": {"type": "text"}}
        self.store.save(Widget("alert_box", HTML, "", JS, fields, VALUES))
        self.asked: list[str] = []

        def server(request: httpx.Request) -> httpx.Response:
            self.asked.append(str(request.url))
            if "gone" in request.url.path:
                return httpx.Response(404)
            return httpx.Response(200, content=b"bytes of " + request.url.path.encode())

        self.media = StreamElementsMedia(self.store, httpx.MockTransport(server))

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_files_at_streamelements_in_the_code_and_the_values_are_found_and_questions_arent(self) -> None:
        self.assertEqual(StreamElementsMedia.named(self.store.get("alert_box")), [
            "cdn/uploads/lizard.png", "cdn/static/theme/Intro.WEBM", "cdn/uploads/removed_link.gif",
            "cdn/uploads/gone.mp3", "cdn/uploads/ding.ogg"])
        self.assertEqual(StreamElementsMedia.named(Widget("plain", "<p>hi</p>")), [])

    async def test_kept_files_are_in_the_widgets_folder_and_its_stand_in_serves_them(self) -> None:
        count, missed = await self.media.keep("alert_box")
        self.assertEqual((count, missed), (4, ["https://cdn.streamelements.com/uploads/gone.mp3"]))
        self.assertIn("https://cdn.streamelements.com/uploads/lizard.png", self.asked)  # asked without ?v=2
        kept = self.store.streamelements_media("alert_box")
        self.assertEqual(self.store.media_file("alert_box", kept["cdn/static/theme/Intro.WEBM"]).suffix, ".webm")

        app = FastAPI()
        page = WidgetPage(WidgetSession())
        app.include_router(build_widget_router(self.store, WidgetHub(WidgetSession()), page))
        client = TestClient(app)
        stand_in = "/overlay/widget/alert_box/streamelements"
        self.assertEqual(client.get(stand_in + "/cdn/uploads/lizard.png?v=2").content, b"bytes of /uploads/lizard.png")
        self.assertEqual(client.get(stand_in + "/cdn/uploads/ding.ogg").content, b"bytes of /uploads/ding.ogg")
        self.assertEqual(client.get(stand_in + "/cdn/uploads/gone.mp3").status_code, 404)  # not here, not asked for
        self.assertEqual(client.get(stand_in + "/cdn/uploads/other.png").status_code, 404)

        # the page asks the stand-in, in the code and in the value his code gets for the field
        built = page.render(self.store.get("alert_box"))
        self.assertNotIn("streamelements.com", built)
        self.assertIn(f'src="{stand_in}/cdn/uploads/lizard.png?v=2"', built)
        self.assertEqual(page.field_data(self.store.get("alert_box"))["alertSound"],
                         stand_in + "/cdn/uploads/ding.ogg")
        self.assertEqual(self.store.get("alert_box").values, VALUES)  # his files stay as written

    async def test_a_kept_file_that_is_gone_isnt_served_and_an_unknown_widget_is_said(self) -> None:
        await self.media.keep("alert_box")
        kept = self.store.streamelements_media("alert_box")
        self.store.media_file("alert_box", kept["cdn/uploads/lizard.png"]).unlink()
        self.assertNotIn("cdn/uploads/lizard.png", self.store.streamelements_media("alert_box"))
        self.assertEqual(self.store.streamelements_media("no_such_widget"), {})
        with self.assertRaises(KeyError):
            await self.media.keep("no_such_widget")


if __name__ == "__main__":
    unittest.main()
