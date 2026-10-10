"""The converter for StreamElements addresses in a widget's code: every link to streamelements.com becomes a
link to the toolbox's own stand-in (widget_router: /overlay/streamelements/...), so the code never calls
StreamElements and keeps working without it.

    https://api.streamelements.com/kappa/v2/channels/x  →  /overlay/streamelements/api/kappa/v2/channels/x
    //cdn.streamelements.com/static/a.png               →  /overlay/streamelements/cdn/static/a.png
    https://streamelements.com/dashboard                →  /overlay/streamelements/www/dashboard

The part before streamelements.com (api, cdn, ...) is kept as the first piece of the path, so the stand-in
knows what was asked. The new address has no host: it is whatever toolbox serves the page (this PC, any port).

That is the form kept in a widget's code. On the widget's page every such address gets the widget in it
(for_widget: /overlay/widget/<name>/streamelements/...), so the stand-in knows which widget asks and keeps
what it gathers in that widget's own data folder.
"""
import re

LINK = re.compile(r"(?:(?:https?|wss?):)?//((?:[a-z0-9-]+\.)*)streamelements\.com(?![\w.-])(?::\d+)?",
                  re.IGNORECASE)
LOCAL = "/overlay/streamelements"


def for_widget(code: str, name: str) -> str:
    """The code as the widget's page runs it: StreamElements addresses, and the toolbox form of them that
    "Remove StreamElements links" wrote, all point at this widget's own stand-in."""
    return without_streamelements_links(code)[0].replace(LOCAL + "/", f"/overlay/widget/{name}/streamelements/")


def without_streamelements_links(code: str) -> tuple[str, int]:
    """The code with every StreamElements address pointing at the toolbox, and how many were changed."""
    return LINK.subn(lambda found: f"{LOCAL}/{found.group(1).rstrip('.').casefold() or 'www'}", code)
