import json
import tempfile
import unittest
from pathlib import Path

import httpx

from streamer_toolbox.core.widgets.streamelements_elements import StreamElementsElements
from streamer_toolbox.core.widgets.streamelements_import import StreamElementsImport
from streamer_toolbox.core.widgets.widget_page import WidgetPage
from streamer_toolbox.core.widgets.widget_session import WidgetSession
from streamer_toolbox.core.widgets.widget_store import WidgetStore

INSTANCE = "ee5253d8-8801-4aac-81ed-f5727171c5ce"
CDN = "https://cdn.streamelements.com/widgets-cms/uploads"
FONT = {"mimeType": "text/css", "href": "https://fonts.googleapis.com/css2", "role": "font-face"}
# the shape StreamElements' API gives (seen 2026-10-03), cut down: a label that is always there and a follow alert
CONFIG = {"boundingBox": {"width": 1920, "height": 1080}, "configStates": [
    {"referenceId": "background", "displayName": "Background",
     "triggers": [{"systemCondition": {}, "userCondition": {}}],
     "settings": {"compositeFields": {
         "Background": {"type": "video", "media": [
             {"href": f"{CDN}/back.png?_meta=abc", "mimeType": "image/png", "role": "placeholder"},
             {"href": f"{CDN}/back.webm?_meta=abc", "mimeType": "video/webm"},
             {"href": f"{CDN}/back.mov?_meta=abc", "mimeType": "video/quicktime"}], "style": {"top": "0px"}},
         "Latest Follower": {"type": "text", "media": [dict(FONT)], "style": {"fontFamily": "Teko"},
                             "text": [{"content": "LATEST FOLLOWER: {session.twitch.follower-latest.name}"}]}}}},
    {"referenceId": "platformEvents", "categoryId": "follower",
     "triggers": [{"systemCondition": {"and": [{"==": [{"var": "event.topic"}, "event"]},
                                               {"==": [{"var": "event.type"}, "follow"]}]}, "userCondition": {}}],
     "settings": {"compositeFields": {
         "Alert sound": {"type": "audio", "media": [{"href": f"{CDN}/ding.mp3", "mimeType": "audio/mpeg"}]},
         "Followed Text": {"type": "text", "media": [dict(FONT)], "style": {"fontFamily": "Teko"},
                           "text": [{"content": "{event.data.username} just followed"}]}}}}]}
SHEET = "@font-face { font-family: 'Teko'; src: url(https://fonts.gstatic.com/s/teko/v1/latin.woff2) format('woff2'); }"


class TestStreamElementsElements(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        folder = Path(self._dir.name)
        (folder / "token.txt").write_text("my.jwt.token\nchannel1\n", encoding="utf-8")
        self.store = WidgetStore(folder / "widgets")
        self.asked: list[httpx.Request] = []
        self.gone: set[str] = set()  # addresses that answer 404

        def handler(request: httpx.Request) -> httpx.Response:
            self.asked.append(request)
            url = str(request.url)
            if url in self.gone:
                return httpx.Response(404)
            if url.endswith(f"/widgets/channel1/{INSTANCE}"):
                return httpx.Response(200, json={"widgetInstance": {
                    "widgetInstanceId": INSTANCE, "displayName": "Anime Theme Package - Stream Ended",
                    "widgetInstancePublishedConfigVersionId": "v2"}})
            if url.endswith("/config-version"):
                return httpx.Response(200, json=[
                    {"widgetInstanceConfigVersionId": "v1", "configData": json.dumps({"configStates": []})},
                    {"widgetInstanceConfigVersionId": "v2", "configData": json.dumps(CONFIG)}])
            if url.endswith("/widgets/channel1"):
                return httpx.Response(200, json=[{"widgetInstance": {"widgetInstanceId": INSTANCE,
                                                                     "displayName": "Stream Ended"}}])
            if request.url.host == "fonts.googleapis.com":
                return httpx.Response(200, text=SHEET)
            return httpx.Response(200, content=b"bytes of " + request.url.path.encode())

        transport = httpx.MockTransport(handler)
        self.elements = StreamElementsElements(StreamElementsImport(folder / "token.txt", transport), transport)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_the_elements_id_from_what_he_pastes(self) -> None:
        pasted = f"https://widgets.streamelements.com/widgets/editor/6884fe693b03cd3ec109f323/{INSTANCE}"
        self.assertEqual(StreamElementsElements.instance_id(pasted), INSTANCE)
        self.assertEqual(StreamElementsElements.instance_id(INSTANCE.upper()), INSTANCE)
        # an overlay's address is not an Element: the widget import takes that one
        self.assertEqual(StreamElementsElements.instance_id("https://streamelements.com/overlay/68a62103cd118ec304786523/editor"), "")

    async def test_lists_his_elements(self) -> None:
        self.assertEqual(await self.elements.elements(), {INSTANCE: "Stream Ended"})
        self.assertEqual(self.asked[0].headers["authorization"], "Bearer my.jwt.token")

    async def test_takes_the_published_settings(self) -> None:
        title, config = await self.elements.fetch(INSTANCE)
        self.assertEqual((title, len(config["configStates"])), ("Anime Theme Package - Stream Ended", 2))
        self.assertTrue(all(request.method == "GET" for request in self.asked))  # it only reads

    async def test_it_becomes_a_widget_with_its_files_on_this_pc(self) -> None:
        widget, missed = await self.elements.bring(INSTANCE, self.store)
        self.assertEqual((widget.name, missed), ("anime_theme_package_stream_ended", []))
        self.assertIn("/static/overlay/element.js", widget.html)
        config = json.loads(widget.js.removeprefix("TOOLBOX_ELEMENT.show(").removesuffix(");"))
        fields = config["configStates"][0]["settings"]["compositeFields"]
        video = fields["Background"]["media"]
        self.assertEqual([m["mimeType"] for m in video], ["video/webm"])  # no placeholder, no .mov
        self.assertEqual(self.store.media_file(widget.name, video[0]["href"]).read_bytes(),
                         b"bytes of /widgets-cms/uploads/back.webm")
        # the font's sheet names the font file here, and both are in the media folder
        sheet = self.store.media_file(widget.name, fields["Latest Follower"]["media"][0]["href"]).read_text("utf-8")
        self.assertNotIn("https://", sheet)
        font = sheet.split("url(")[1].split(")")[0]
        self.assertTrue(font.endswith(".woff2") and self.store.media_file(widget.name, font))
        asked = [str(request.url) for request in self.asked]
        self.assertIn("https://fonts.googleapis.com/css2?family=Teko:wght@400;700&display=swap", asked)
        self.assertEqual(sum(1 for url in asked if "fonts.googleapis.com" in url), 1)  # the same font once
        self.assertFalse(any(url.endswith((".mov?_meta=abc", ".png?_meta=abc")) for url in asked))
        self.assertFalse(any("authorization" in request.headers for request in self.asked[2:]))  # the token stays home

    async def test_the_page_names_no_other_host(self) -> None:
        widget, _ = await self.elements.bring(INSTANCE, self.store)
        page = WidgetPage(WidgetSession()).render(self.store.get(widget.name))
        self.assertNotIn("streamelements.com", page)
        self.assertNotIn("googleapis", page)
        self.assertIn("{event.data.username} just followed", page)  # the words stay as written

    async def test_a_file_that_cant_be_fetched_is_named(self) -> None:
        self.gone.add(f"{CDN}/ding.mp3")
        widget, missed = await self.elements.bring(INSTANCE, self.store)
        self.assertEqual(missed, [f"{CDN}/ding.mp3"])
        self.assertIn(f"{CDN}/ding.mp3", widget.js)

    async def test_a_second_import_gets_a_name_of_its_own(self) -> None:
        await self.elements.bring(INSTANCE, self.store)
        widget, _ = await self.elements.bring(INSTANCE, self.store)
        self.assertEqual(widget.name, "anime_theme_package_stream_ended_2")

    async def test_says_what_is_wrong(self) -> None:
        with self.assertRaisesRegex(ValueError, "not a StreamElements Element"):
            await self.elements.fetch("https://streamelements.com/dashboard")
        self.gone.add(f"https://api.streamelements.com/kappa/v3/widgets/channel1/{INSTANCE}")
        with self.assertRaisesRegex(KeyError, "no such Element"):
            await self.elements.fetch(INSTANCE)


if __name__ == "__main__":
    unittest.main()
