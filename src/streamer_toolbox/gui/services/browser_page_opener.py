import webbrowser

from streamer_toolbox.core.interfaces.page_opener import PageOpener


class BrowserPageOpener(PageOpener):
    """Opens the dashboard as a tab in the default browser."""

    def open(self, url: str) -> None:
        webbrowser.open(url)
