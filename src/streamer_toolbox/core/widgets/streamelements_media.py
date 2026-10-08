import hashlib
import re

import httpx

from streamer_toolbox.core.widgets.widget import Widget
from streamer_toolbox.core.widgets.widget_store import WidgetStore

# a file at StreamElements as a widget names it: the real address, or the toolbox form of it that "Remove
# StreamElements links" wrote. Group 1 / 3: the part before streamelements.com (cdn, ...), group 2 / 4: the path
FILE = re.compile(r"""(?:(?:https?:)?//((?:[a-z0-9-]+\.)*)streamelements\.com(?::\d+)?/([^\s"'<>()\\]+)"""
                  r"""|/overlay/streamelements/([a-z0-9.-]+)/([^\s"'<>()\\]+))""", re.IGNORECASE)
ENDING = re.compile(r"\.(png|jpe?g|gif|webp|avif|svg|webm|mp4|mov|mp3|ogg|wav|m4a|woff2?|ttf|otf|js|css|json)$",
                    re.IGNORECASE)
BIGGEST = 200 * 1024 * 1024  # bytes: a scene's video can be large; beyond this it is left out


class StreamElementsMedia:
    """The files a widget loads from StreamElements' servers (cdn.streamelements.com: pictures, sounds, videos,
    fonts, helper scripts), named in its code or in the values of its fields. keep() fetches them once into the
    widget's media folder; the widget's stand-in for StreamElements (widget_router) then answers with those
    copies, so the widget shows everything without StreamElements being asked. The widget's code and values
    stay as written.

    Whether he may copy a file is his to check (the import asks): what he uploaded is his; StreamElements'
    own library and other people's themes are theirs, and StreamElements' terms don't allow copying their
    content out."""

    def __init__(self, store: WidgetStore, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._store = store
        self._transport = transport

    @staticmethod
    def named(widget: Widget) -> list[str]:
        """The StreamElements files the widget names, each as "<host part>/<path>" ("cdn/uploads/a.png"), the
        way the stand-in is asked for it. Their API (questions, not files) isn't among them."""
        code = "\n".join((widget.html, widget.css, widget.js, *_texts(widget.values), *_texts(widget.fields)))
        found: list[str] = []
        for match in FILE.finditer(code):
            host = (match.group(1) or match.group(3) or "").rstrip(".").casefold() or "www"
            path = (match.group(2) or match.group(4)).split("?")[0].split("#")[0]
            key = f"{host}/{path}"
            if host != "api" and ENDING.search(path) and key not in found:
                found.append(key)
        return found

    async def keep(self, name: str) -> tuple[int, list[str]]:
        """Fetches every StreamElements file the widget names (again, if kept before). Gives how many are kept
        now and the ones that couldn't be fetched."""
        widget = self._store.get(name)
        if widget is None:
            raise KeyError(f"there's no widget {name!r}")
        kept: dict[str, str] = {}
        missed: list[str] = []
        async with httpx.AsyncClient(transport=self._transport, timeout=120, follow_redirects=True) as client:
            for key in self.named(widget):
                host, path = key.split("/", 1)
                address = f"https://{'' if host == 'www' else host + '.'}streamelements.com/{path}"
                try:
                    answer = await client.get(address)
                    answer.raise_for_status()
                except (httpx.HTTPError, ValueError):
                    missed.append(address)
                    continue
                if len(answer.content) > BIGGEST:
                    missed.append(address)
                    continue
                file = "se_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:16] + ENDING.search(path).group(0).lower()
                self._store.save_media(name, file, answer.content)
                kept[key] = file
        self._store.set_streamelements_media(name, kept)
        return len(kept), missed


def _texts(value: object) -> list[str]:
    """Every text inside a value (fields and their values can be nested)."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for part in value.values() for text in _texts(part)]
    if isinstance(value, (list, tuple)):
        return [text for part in value for text in _texts(part)]
    return []
