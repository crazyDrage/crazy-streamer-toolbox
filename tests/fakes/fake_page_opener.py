from streamer_toolbox.core.interfaces.page_opener import PageOpener


class FakePageOpener(PageOpener):
    def __init__(self) -> None:
        self.opened: list[str] = []

    def open(self, url: str) -> None:
        self.opened.append(url)
