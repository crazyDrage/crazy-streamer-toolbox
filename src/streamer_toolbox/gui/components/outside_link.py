import webbrowser
from collections.abc import Callable

from nicegui import ui

from streamer_toolbox.core.security.remote_access import RemoteAccess


def outside_link(text: str, url: str, open_here: Callable[[str], object] = webbrowser.open) -> ui.link:
    """A link to a page outside the toolbox (a program's docs, a service's token page). Clicked on this PC it
    opens in the system's default browser: the toolbox's own window is a bare browser window without his
    logins, bookmarks or password manager, and a new tab there is the wrong place for Twitch's or Google's
    pages. Clicked on another device (his phone) it opens there, as a new tab, like any link."""
    link = ui.link(text, url, new_tab=True)
    request = getattr(ui.context.client, "request", None)
    if RemoteAccess.is_this_pc(request.client.host if request and request.client else None):
        link.on("click.prevent", lambda: open_here(url))
    return link
