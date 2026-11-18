class DeckPager:
    """A flow asked the open Live pages to show a page (box Show Live page; his 11-18 pick 13: e.g. OBS scene
    Gaming → the gaming buttons). Open Live pages that aren't being edited follow when `version` goes up."""

    def __init__(self) -> None:
        self.page = ""
        self.version = 0

    def show(self, page: str) -> None:
        self.page = page
        self.version += 1
