from streamer_toolbox.core.deck.deck_pager import DeckPager
from streamer_toolbox.core.deck.deck_store import DeckStore
from streamer_toolbox.core.interfaces.box import Box


class ShowLivePage(Box):
    """Every open Live page shows this page of the deck (his 11-18 pick 13: e.g. OBS scene Gaming → the gaming
    buttons, like Stream Deck switching profiles by the app in front). A Live page being edited stays where it is."""

    name = "show_page"
    label = "Show Live page"
    help = "Every open Live page (phone, tablet, the toolbox) shows this page of buttons. One being edited stays"
    group = "Live"
    hints = {"page": "The page's name, as in the Live side list"}

    def __init__(self, pager: DeckPager, store: DeckStore) -> None:
        self._pager = pager
        self._store = store

        async def pages() -> list[str]:
            return [p.name for p in self._store.load().pages]

        self.options = {"page": pages}

    async def run(self, page: str) -> str:
        """The page now shown."""
        page = str(page).strip()
        if self._store.load().page(page) is None:
            raise ValueError(f"the Live deck has no page {page!r}")
        self._pager.show(page)
        return page
