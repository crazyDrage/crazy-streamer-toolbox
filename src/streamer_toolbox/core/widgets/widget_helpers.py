import hashlib
import re
from urllib.parse import urljoin

import httpx

from streamer_toolbox.core.web.web_client import web_client
from streamer_toolbox.core.widgets.widget import Widget
from streamer_toolbox.core.widgets.widget_store import WidgetStore

TAG = re.compile(r"<(script|link)\b[^>]*>", re.IGNORECASE)
ADDRESS = re.compile(r"""\b(?:src|href)\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s>]+))""", re.IGNORECASE)
STYLESHEET = re.compile(r"""\brel\s*=\s*["']?[^"'>]*stylesheet""", re.IGNORECASE)
# a kept file's content is no longer the other server's: its check value and its "ask with permission" go
CHECKS = re.compile(r"""\s(?:integrity|crossorigin)(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+))?""", re.IGNORECASE)
OUTSIDE = re.compile(r"(?:https?:)?//", re.IGNORECASE)
SHEET_URL = re.compile(r"""url\(\s*["']?([^"')\s]+)["']?\s*\)""")
ENDING = re.compile(r"\.[A-Za-z0-9]{1,5}$")
BROWSER = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/126.0 Safari/537.36"}  # font services give the small modern files to a browser
BIGGEST = 10 * 1024 * 1024  # bytes: a helper script or a font is far below this
MOST_IN_A_SHEET = 60        # files a style sheet may pull in (an icon font names a handful)


class WidgetHelpers:
    """The helper scripts and style sheets a widget's HTML loads from other people's servers (`<script src>`,
    `<link rel="stylesheet" href>`: jQuery plugins, chat libraries, fonts). Loaded from there, whoever runs
    that server decides what runs in the widget, each time the page opens. keep() fetches them once into the
    widget's media folder (a style sheet with the files it names: fonts, pictures), and the page then loads
    those copies (WidgetPage; the widget's own code stays as written). They don't change any more, and the
    widget works without the internet. drop() goes back to loading from the other servers.

    Only what the HTML names in such a tag is kept: a script that the widget's code loads by itself while
    it runs isn't seen here (the allowed hosts on the Safety tab still cover it)."""

    def __init__(self, store: WidgetStore, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._store = store
        self._transport = transport

    @staticmethod
    def named(widget: Widget) -> list[str]:
        """The outside addresses the widget's HTML loads scripts and style sheets from, as written, in order."""
        found: list[str] = []
        for tag in TAG.finditer(widget.html):
            address = _address(tag.group(0))
            if address and OUTSIDE.match(address) and address not in found and \
                    (tag.group(1).lower() == "script" or STYLESHEET.search(tag.group(0))):
                found.append(address)
        return found

    async def keep(self, name: str) -> tuple[int, list[str]]:
        """Fetches every helper the widget names (again, if it was kept before). Gives how many are kept now
        and the addresses that couldn't be fetched (those keep loading from their server)."""
        widget = self._store.get(name)
        if widget is None:
            raise KeyError(f"there's no widget {name!r}")
        kept: dict[str, str] = {}
        missed: list[str] = []
        async with web_client(self._transport, timeout=30, follow_redirects=True,
                                     headers=BROWSER) as client:
            for address in self.named(widget):
                full = "https:" + address if address.startswith("//") else address
                content = await _fetch(client, full)
                if content is None:
                    missed.append(address)
                    continue
                sheet = full.split("?")[0].lower().endswith(".css") or b"@font-face" in content[:4096]
                if sheet:
                    content = await self._with_its_files(client, name, full, content)
                file = _file_name(full, ".css" if sheet else ".js")
                self._store.save_media(name, file, content)
                kept[address] = file
        self._store.set_helpers(name, kept)
        return len(kept), missed

    def drop(self, name: str) -> None:
        """The widget loads its helpers from their servers again. The fetched files stay in the media folder
        (an Element's own files are there too); nothing names them any more."""
        self._store.set_helpers(name, {})

    async def _with_its_files(self, client: httpx.AsyncClient, name: str, sheet_address: str,
                              content: bytes) -> bytes:
        """A style sheet with the files it names fetched too and named by their local names."""
        sheet = content.decode("utf-8", "replace")
        done: dict[str, str] = {}
        for written in SHEET_URL.findall(sheet):
            if written in done or written.startswith(("data:", "#")) or len(done) >= MOST_IN_A_SHEET:
                continue
            full = urljoin(sheet_address, written)
            fetched = await _fetch(client, full)
            if fetched is not None:
                done[written] = _file_name(full)
                self._store.save_media(name, done[written], fetched)
        return SHEET_URL.sub(lambda m: f"url({done[m.group(1)]})" if m.group(1) in done else m.group(0),
                             sheet).encode("utf-8")


def with_kept_helpers(html: str, name: str, kept: dict[str, str]) -> str:
    """The widget's HTML with every kept helper loaded from the widget's own media folder."""
    if not kept:
        return html

    def local(tag: re.Match) -> str:
        text = tag.group(0)
        address = _address(text)
        if address not in kept:
            return text
        return CHECKS.sub("", text.replace(address, f"/overlay/widget/{name}/media/{kept[address]}"))

    return TAG.sub(local, html)


def _address(tag: str) -> str:
    found = ADDRESS.search(tag)
    return next((part for part in found.groups() if part), "").strip() if found else ""


async def _fetch(client: httpx.AsyncClient, address: str) -> bytes | None:
    try:
        answer = await client.get(address)
        answer.raise_for_status()
    except (httpx.HTTPError, ValueError):
        return None
    return answer.content if len(answer.content) <= BIGGEST else None


def _file_name(address: str, ending: str = "") -> str:
    """A file name of its own for an address: the same address is the same file."""
    found = ENDING.search(address.split("?")[0].split("#")[0])
    return "helper_" + hashlib.sha1(address.encode("utf-8")).hexdigest()[:16] + \
        (ending or (found.group(0).lower() if found else ""))
