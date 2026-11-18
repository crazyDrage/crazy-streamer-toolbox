import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.deck.boxes.show_live_page import ShowLivePage
from streamer_toolbox.core.deck.deck import Deck
from streamer_toolbox.core.deck.deck_page import DeckPage
from streamer_toolbox.core.deck.deck_pager import DeckPager
from streamer_toolbox.core.deck.deck_store import DeckStore


class TestShowLivePage(unittest.IsolatedAsyncioTestCase):
    """His 11-18 pick 13: a flow turns the open Live pages to a page."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = DeckStore(Path(self.tmp.name) / "live_deck.json", lambda: [])
        self.store.save(Deck([DeckPage("Main"), DeckPage("Gaming")]))
        self.pager = DeckPager()
        self.box = ShowLivePage(self.pager, self.store)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    async def test_it_asks_the_open_pages_to_show_the_page(self) -> None:
        self.assertEqual(await self.box.run("Gaming "), "Gaming")
        self.assertEqual((self.pager.page, self.pager.version), ("Gaming", 1))
        self.assertEqual(await self.box.options["page"](), ["Main", "Gaming"])

    async def test_a_page_the_deck_does_not_have_fails(self) -> None:
        with self.assertRaises(ValueError):
            await self.box.run("Nope")
        self.assertEqual(self.pager.version, 0)
