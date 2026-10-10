import json
import re
from collections.abc import Callable
from html import escape
from typing import Any

from streamer_toolbox.core.app_name import APP_NAME
from streamer_toolbox.core.widgets.streamelements_links import for_widget
from streamer_toolbox.core.widgets.widget import Widget
from streamer_toolbox.core.widgets.widget_helpers import with_kept_helpers
from streamer_toolbox.core.widgets.widget_session import WidgetSession

DOUBLE = re.compile(r"\{\{\s*([\w-]+)\s*\}\}")
SINGLE = re.compile(r"\{([\w-]+)\}")
CURRENCY = {"code": "USD", "name": "U.S. Dollar", "symbol": "$"}


class WidgetPage:
    """Builds a widget's overlay page the way StreamElements does: his field values are put into the HTML, CSS
    and JS where the code says {{field}} (HTML and CSS also {field}), then one page with the CSS, the HTML, the
    toolbox's stand-in for StreamElements' page code (static/overlay/widget.js: SE_API, the events), jQuery
    (StreamElements' overlay page has it, so widgets use `$` without loading it) and the widget's JS. Where the code
    has a StreamElements address (api.streamelements.com/..., cdn.streamelements.com/...), the page has the
    toolbox's own stand-in instead (streamelements_links; widget_router: .../<name>/streamelements/...), so the
    page never calls StreamElements and works without it, also for code where he didn't press "Remove
    StreamElements links" (that changes the widget's files; this only the page). Field values are text put into code he chose to
    run, so nothing is escaped, as on StreamElements."""

    def __init__(self, session: WidgetSession, channel: Callable[[], dict[str, str]] | None = None) -> None:
        self._session = session
        # the streamer's Twitch login name ("username") and id ("providerId") and StreamElements account id
        # ("id"), asked for when a page is built
        self._channel = channel or (lambda: {})

    def render(self, widget: Widget, helpers: dict[str, str] | None = None) -> str:
        """helpers: the helper scripts kept on this PC (WidgetStore.helpers); the page loads those copies."""
        data = self.field_data(widget)
        html = with_kept_helpers(fill(widget.html, data, single=True), widget.name, helpers or {})
        start = {"name": widget.name, "detail": self.load_detail(data)}
        return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{escape(widget.name)} · {APP_NAME} widget</title>
<style>html, body {{ margin: 0; background: transparent; overflow: hidden; }}</style>
<style>
{_no_close(for_widget(fill(widget.css, data, single=True), widget.name), "style")}
</style>
<script>window.TOOLBOX_WIDGET = {_json(start)};</script>
<script src="/static/overlay/widget.js"></script>
<script src="/static/overlay/vendor/jquery.min.js"></script>
</head>
<body>
{_framed(for_widget(html, widget.name), widget.frame)}
<script>
{_no_close(for_widget(fill(widget.js, data, single=False), widget.name), "script")}
</script>
<script>window.TOOLBOX_WIDGET.start();</script>
</body>
</html>
"""

    @staticmethod
    def shell(name: str, query: str = "", sandbox: str = "allow-scripts") -> str:
        """The page OBS opens: nothing but a see-through frame with the widget's page (render) in it. The shell
        is the toolbox's own, so its headers (WidgetSafety.shell_headers) can keep the frame on that page: the
        widget's code can't send the page to another site. query: the address's own (?preview=1), passed on."""
        address = f"/overlay/widget/{name}/page" + (f"?{query}" if query else "")
        return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{escape(name)} · {APP_NAME} widget</title>
<style>
html, body {{ margin: 0; height: 100%; background: transparent; overflow: hidden; }}
iframe {{ display: block; width: 100%; height: 100%; border: 0; background: transparent; }}
</style>
</head>
<body>
<iframe src="{escape(address)}" sandbox="{escape(sandbox)}" allow="autoplay *"></iframe>
</body>
</html>
"""

    def field_data(self, widget: Widget) -> dict[str, Any]:
        """The fieldData his code gets; a picture / video / sound field holds the address the page loads the file
        from (the file itself is on this PC), "" if none is picked."""
        data = widget.field_data()
        for key in widget.media_fields():
            value = str(data.get(key) or "").strip()
            if not value.casefold().startswith(("http://", "https://")):  # a web address is used as it is
                data[key] = f"/overlay/widget/{widget.name}/file/{key}" if value else ""
        # a StreamElements address in a value (a picture or sound picked there) goes to the widget's stand-in,
        # like the ones in the code: a copy kept on this PC is served from there
        return {key: for_widget(value, widget.name) if isinstance(value, str) else value
                for key, value in data.items()}

    def load_detail(self, field_data: dict[str, Any]) -> dict[str, Any]:
        """obj.detail of onWidgetLoad."""
        channel = self._channel()
        return {"session": {"data": self._session.data}, "recents": self._session.recents, "currency": CURRENCY,
                "channel": {"username": channel.get("username", ""), "apiToken": "", "id": channel.get("id", ""),
                            "providerId": channel.get("providerId", ""), "avatar": ""},
                "fieldData": field_data, "overlay": {"isEditorMode": False, "muted": False}}


def fill(code: str, data: dict[str, Any], single: bool) -> str:
    """{{field}} → its value; with single also {field} (HTML and CSS: in JS that would hit `const {name} = ...`).
    A name that isn't a field stays as it is."""
    def value(match: re.Match) -> str:
        key = match.group(1)
        return _text(data[key]) if key in data else match.group(0)

    code = DOUBLE.sub(value, code)
    return SINGLE.sub(value, code) if single else code


def _framed(html: str, frame: dict[str, Any]) -> str:
    """The widget's HTML inside the box it had on the StreamElements overlay (its code may count on that size)."""
    if not frame:
        return html
    style = "; ".join(f"{key}: {_length(frame[key])}" for key in ("left", "top", "width", "height") if key in frame)
    return f'<div class="toolbox-widget-frame" style="position: absolute; {style}">\n{html}\n</div>'


def _length(value: Any) -> str:
    """StreamElements keeps sizes as numbers (pixels) or as text with a unit; only a plain length gets through."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{value:g}px"
    found = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*(px|%|vw|vh)?\s*", str(value))
    return f"{found.group(1)}{found.group(2) or 'px'}" if found else "auto"


def _text(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return "" if value is None else str(value)


def _json(value: Any) -> str:
    """JSON that is safe inside a <script>: no way to close the tag from a viewer's name or message."""
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def _no_close(code: str, tag: str) -> str:
    """Code that says </script> (or </style>) in a string would end our tag early."""
    return re.sub(rf"</({tag})", r"<\\/\1", code, flags=re.IGNORECASE)
