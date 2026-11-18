import json
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from streamer_toolbox.api.font_router import build_font_router
from streamer_toolbox.core.fonts.font_library import FontLibrary
from tests.fakes.tiny_font import TinyFont


class TestFontRouter(unittest.TestCase):
    """His 11-18: "every font loads it from the endpoint"; a widget's sandboxed page needs the CORS header."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "fonts.json").write_text(json.dumps({"this_machine": ["Impact"]}), encoding="utf-8")
        library = FontLibrary(root / "fonts", root / "fonts.json")
        TinyFont.make(library.folder / "Bangers.ttf", "Bangers")
        app = FastAPI()
        app.include_router(build_font_router(library))
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_the_css_and_the_file(self) -> None:
        css = self.client.get("/toolbox/fonts/fonts.css")
        self.assertEqual(css.status_code, 200)
        self.assertIn('url("/toolbox/fonts/file/Bangers.ttf")', css.text)
        self.assertEqual(css.headers["access-control-allow-origin"], "*")
        font = self.client.get("/toolbox/fonts/file/Bangers.ttf")
        self.assertEqual((font.status_code, font.headers["content-type"]), (200, "font/ttf"))
        self.assertEqual(font.headers["access-control-allow-origin"], "*")

    def test_nothing_else_is_served(self) -> None:
        for address in ("/toolbox/fonts/file/fonts.json", "/toolbox/fonts/file/..%2Ffonts.json",
                        "/toolbox/fonts/file/nope.ttf"):
            self.assertEqual(self.client.get(address).status_code, 404, address)
