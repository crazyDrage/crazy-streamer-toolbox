import json
import tempfile
import unittest
from pathlib import Path

import httpx

from streamer_toolbox.core.widgets.streamelements_import import StreamElementsImport
from streamer_toolbox.core.widgets.widget_page import WidgetPage
from streamer_toolbox.core.widgets.widget_session import WidgetSession
from streamer_toolbox.core.widgets.widget_store import WidgetStore

OVERLAY_ID = "68a62103cd118ec304786523"
# the shape StreamElements' API gives (seen 2026-10-03), cut down: one custom widget, one of their own
OVERLAY = {"_id": OVERLAY_ID, "name": "Next Activity!", "widgets": [
    {"id": 1, "type": "se-widget-custom-event-list", "name": None,
     "css": {"z-index": 2, "width": 1000, "height": 1000, "opacity": 1, "top": "1.04px", "left": "3.49px"},
     "variables": {"html": "<div id='wheel'>{{wheelName}}</div>", "css": "#wheel { font-size: {fontSize}px; }",
                   "js": "console.log('LOAD');",
                   "fields": json.dumps({"wheelName": {"type": "text", "label": "Name", "value": ""},
                                         "fontSize": {"type": "number", "label": "Size", "value": 20},
                                         "foregroundImage": {"type": "image-input", "label": "Picture"}}),
                   "fieldData": {"wheelName": "Spin!", "fontSize": 40,
                                 "foregroundImage": "https://example.org/wheel.png"}}},
    {"id": 2, "type": "se-widget-alertbox", "name": "AlertBox", "css": {"width": 800}}]}


class TestStreamElementsImport(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.token = Path(self._dir.name) / "streamelements_token.txt"
        self.asked: list[httpx.Request] = []
        self.answer = httpx.Response(200, json=OVERLAY)

        def handler(request: httpx.Request) -> httpx.Response:
            self.asked.append(request)
            return self.answer

        self.importer = StreamElementsImport(self.token, httpx.MockTransport(handler))

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_the_overlays_id_from_what_he_pastes(self) -> None:
        for pasted in (f"https://streamelements.com/overlay/{OVERLAY_ID}/editor?er=1",
                       f" https://streamelements.com/overlay/{OVERLAY_ID.upper()}/abc ", OVERLAY_ID):
            self.assertEqual(StreamElementsImport.overlay_id(pasted), OVERLAY_ID)
        with self.assertRaisesRegex(ValueError, "not a StreamElements overlay"):
            StreamElementsImport.overlay_id("https://streamelements.com/dashboard")

    async def test_asks_streamelements_with_the_token_read_only(self) -> None:
        self.token.write_text("my.jwt.token\nchannel1\n", encoding="utf-8")
        overlay = await self.importer.fetch(f"https://streamelements.com/overlay/{OVERLAY_ID}/editor")
        self.assertEqual(overlay["name"], "Next Activity!")
        request = self.asked[0]
        self.assertEqual((request.method, str(request.url)),
                         ("GET", f"https://api.streamelements.com/kappa/v2/overlays/channel1/{OVERLAY_ID}"))
        self.assertEqual(request.headers["authorization"], "Bearer my.jwt.token")

    async def test_lists_his_overlays_newest_change_first(self) -> None:
        self.token.write_text("my.jwt.token\nchannel1", encoding="utf-8")
        self.answer = httpx.Response(200, json={"docs": [
            {"_id": "a" * 24, "name": "Old", "updatedAt": "2026-01-01T00:00:00Z"},
            {"_id": "b" * 24, "name": "Next Activity", "updatedAt": "2026-10-03T00:00:00Z"}], "total": 2})
        self.assertEqual(list((await self.importer.overlays()).items()),
                         [("b" * 24, "Next Activity"), ("a" * 24, "Old")])
        self.assertEqual(str(self.asked[0].url), "https://api.streamelements.com/kappa/v2/overlays/channel1?limit=100")

    async def test_what_can_go_wrong_says_so(self) -> None:
        with self.assertRaisesRegex(PermissionError, "No token yet"):
            await self.importer.fetch(OVERLAY_ID)
        self.assertEqual(self.importer.account_id(), "")
        self.token.write_text("my.jwt.token\nchannel1", encoding="utf-8")
        self.assertEqual(self.importer.account_id(), "channel1")
        self.answer = httpx.Response(401, json={"message": "Unauthorized"})
        with self.assertRaisesRegex(PermissionError, "refused the token"):
            await self.importer.fetch(OVERLAY_ID)
        self.answer = httpx.Response(404, json={})
        with self.assertRaisesRegex(KeyError, "no such overlay"):
            await self.importer.fetch(OVERLAY_ID)
        self.token.write_text("not-a-jwt", encoding="utf-8")
        with self.assertRaisesRegex(PermissionError, "Account ID on line 2"):
            await self.importer.fetch(OVERLAY_ID)

    def test_a_custom_widget_comes_over_with_its_code_settings_and_place(self) -> None:
        widgets = StreamElementsImport.widgets(OVERLAY, taken=[])
        self.assertEqual(len(widgets), 1)  # their alert box has no code to take
        widget = widgets[0]
        self.assertEqual((widget.name, widget.js), ("next_activity", "console.log('LOAD');"))
        self.assertEqual(widget.field_data(), {"wheelName": "Spin!", "fontSize": 40,
                                               "foregroundImage": "https://example.org/wheel.png"})
        self.assertEqual(widget.frame, {"width": 1000, "height": 1000, "top": "1.04px", "left": "3.49px"})
        self.assertEqual(StreamElementsImport.widgets(OVERLAY, taken=["Next_Activity"])[0].name, "next_activity_2")
        two = {"name": "", "widgets": [OVERLAY["widgets"][0], OVERLAY["widgets"][0]]}
        self.assertEqual([w.name for w in StreamElementsImport.widgets(two, [])],
                         ["streamelements_1", "streamelements_2"])

    def test_an_imported_widget_is_kept_and_drawn_in_its_box(self) -> None:
        store = WidgetStore(Path(self._dir.name) / "widgets")
        store.save(StreamElementsImport.widgets(OVERLAY, [])[0])
        widget = store.get("next_activity")
        self.assertEqual(widget.frame["width"], 1000)
        page = WidgetPage(WidgetSession()).render(widget)
        self.assertIn('style="position: absolute; left: 3.49px; top: 1.04px; width: 1000px; height: 1000px"', page)
        self.assertIn("<div id='wheel'>Spin!</div>", page)
        self.assertIn("font-size: 40px", page)
        self.assertIn('"foregroundImage": "https://example.org/wheel.png"', page)  # a web address stays one
        evil = WidgetPage(WidgetSession()).render(type(widget)("x", "<p></p>", frame={"width": "1px; color: red"}))
        self.assertIn("width: auto", evil)  # only a plain length gets into the style


if __name__ == "__main__":
    unittest.main()
