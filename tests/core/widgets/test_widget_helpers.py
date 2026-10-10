import tempfile
import unittest
from pathlib import Path

import httpx

from streamer_toolbox.core.widgets.widget import Widget
from streamer_toolbox.core.widgets.widget_helpers import WidgetHelpers, with_kept_helpers
from streamer_toolbox.core.widgets.widget_page import WidgetPage
from streamer_toolbox.core.widgets.widget_session import WidgetSession
from streamer_toolbox.core.widgets.widget_store import WidgetStore

HTML = """<script src="https://cdn.example.com/lib/chat.min.js" integrity="sha384-abc" crossorigin="anonymous"></script>
<link href='//fonts.example.com/css?family=Lizard' rel='stylesheet'>
<link rel="icon" href="https://cdn.example.com/icon.png">
<script src="https://gone.example.com/missing.js"></script>
<script src="/static/own.js"></script>
<script>var inline = "https://cdn.example.com/not_a_tag.js";</script>
<div id="chat"></div>"""
SHEET = ("@font-face { font-family: Lizard; src: url(https://files.example.com/lizard.woff2) format('woff2'), "
         "url('../fonts/lizard.ttf'); }\n.dot { background: url(data:image/png;base64,AAAA); }")


class TestWidgetHelpers(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.store = WidgetStore(Path(self._dir.name))
        self.store.save(Widget("chat_box", HTML))
        self.asked: list[str] = []

        def server(request: httpx.Request) -> httpx.Response:
            self.asked.append(str(request.url))
            answers = {"https://cdn.example.com/lib/chat.min.js": b"window.chat = 1;",
                       "https://fonts.example.com/css?family=Lizard": SHEET.encode(),
                       "https://files.example.com/lizard.woff2": b"woff2-bytes",
                       "https://fonts.example.com/fonts/lizard.ttf": b"ttf-bytes"}
            found = answers.get(str(request.url))
            return httpx.Response(200, content=found) if found is not None else httpx.Response(404)

        self.helpers = WidgetHelpers(self.store, httpx.MockTransport(server))

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_only_outside_scripts_and_style_sheets_in_tags_are_helpers(self) -> None:
        self.assertEqual(WidgetHelpers.named(self.store.get("chat_box")), [
            "https://cdn.example.com/lib/chat.min.js", "//fonts.example.com/css?family=Lizard",
            "https://gone.example.com/missing.js"])
        self.assertEqual(WidgetHelpers.named(Widget("plain", "<p>hello</p>")), [])

    async def test_kept_helpers_are_files_of_the_widget_and_the_page_loads_those(self) -> None:
        count, missed = await self.helpers.keep("chat_box")
        self.assertEqual((count, missed), (2, ["https://gone.example.com/missing.js"]))
        kept = self.store.helpers("chat_box")
        self.assertEqual(set(kept), {"https://cdn.example.com/lib/chat.min.js",
                                     "//fonts.example.com/css?family=Lizard"})
        script = self.store.media_file("chat_box", kept["https://cdn.example.com/lib/chat.min.js"])
        self.assertEqual((script.suffix, script.read_bytes()), (".js", b"window.chat = 1;"))
        # the style sheet names its fonts by their local files; a data: picture stays as it is
        sheet = self.store.media_file("chat_box", kept["//fonts.example.com/css?family=Lizard"]).read_text("utf-8")
        self.assertNotIn("example.com", sheet)
        self.assertIn("data:image/png;base64,AAAA", sheet)
        fonts = sorted(p.read_bytes() for p in script.parent.iterdir() if p.suffix in (".woff2", ".ttf"))
        self.assertEqual(fonts, [b"ttf-bytes", b"woff2-bytes"])  # ../fonts/ was taken from the sheet's address

        page = WidgetPage(WidgetSession()).render(self.store.get("chat_box"), kept)
        self.assertIn(f'<script src="/overlay/widget/chat_box/media/{script.name}"></script>', page)
        self.assertNotIn("integrity", page)  # the copy is the toolbox's own file now
        self.assertNotIn("fonts.example.com", page)
        self.assertIn("https://gone.example.com/missing.js", page)  # not fetched: still from its server
        self.assertIn("https://cdn.example.com/icon.png", page)
        self.assertIn('"https://cdn.example.com/not_a_tag.js"', page)  # code is never rewritten
        self.assertEqual(self.store.get("chat_box").html, HTML)  # his file stays as written

    async def test_dropping_them_loads_from_the_servers_again(self) -> None:
        await self.helpers.keep("chat_box")
        self.helpers.drop("chat_box")
        self.assertEqual(self.store.helpers("chat_box"), {})
        page = WidgetPage(WidgetSession()).render(self.store.get("chat_box"), self.store.helpers("chat_box"))
        self.assertIn("https://cdn.example.com/lib/chat.min.js", page)

    async def test_a_kept_file_that_is_gone_isnt_named(self) -> None:
        await self.helpers.keep("chat_box")
        kept = self.store.helpers("chat_box")
        self.store.media_file("chat_box", kept["https://cdn.example.com/lib/chat.min.js"]).unlink()
        self.assertEqual(set(self.store.helpers("chat_box")), {"//fonts.example.com/css?family=Lizard"})
        self.assertEqual(self.store.helpers("no_such_widget"), {})
        with self.assertRaises(KeyError):
            await self.helpers.keep("no_such_widget")

    def test_without_kept_helpers_the_html_is_untouched(self) -> None:
        self.assertEqual(with_kept_helpers(HTML, "chat_box", {}), HTML)


if __name__ == "__main__":
    unittest.main()
