import copy
import hashlib
import json
import re
from typing import Any

import httpx

from streamer_toolbox.core.web.web_client import web_client
from streamer_toolbox.core.widgets.streamelements_import import StreamElementsImport, _free, _slug
from streamer_toolbox.core.widgets.widget import Widget
from streamer_toolbox.core.widgets.widget_store import WidgetStore

API = "https://api.streamelements.com/kappa/v3/widgets"
INSTANCE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
GOOGLE_FONTS = "https://fonts.googleapis.com/css2"
# Google hands out the small woff2 files only to a browser it knows
BROWSER = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/126.0 Safari/537.36"}
FONT_URL = re.compile(r"url\((https://[^)\s]+)\)")
ENDING = re.compile(r"\.[A-Za-z0-9]{1,5}$")
# the page of an imported Element: the toolbox's own code draws it (static/overlay/element.js) from its settings
HTML = '<div id="toolbox-element"></div>\n<script src="/static/overlay/element.js"></script>'
JS = "TOOLBOX_ELEMENT.show({config});"


class StreamElementsElements:
    """Brings one of his StreamElements "Elements" over (the newer kind of widget, widgets.streamelements.com:
    scene packages with labels and alerts, tickers). An Element has no code of its own to take: it is a settings
    file (a canvas size and "states", each a list of pictures, videos, sounds and texts with their place, look
    and animation; a state is always there or is triggered by an event) that StreamElements' page draws. Here
    the toolbox's own page code draws it, so it becomes an ordinary widget: the settings are in its JS part,
    and its pictures, videos, sounds and fonts are fetched once into the widget's media folder, so the page
    needs neither StreamElements nor Google afterwards. Asks StreamElements read only, with the same token
    file as StreamElementsImport."""

    def __init__(self, account: StreamElementsImport, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._account = account
        self._transport = transport

    @staticmethod
    def instance_id(text: str) -> str:
        """The Element's id from what he pasted: the editor's address or the id itself; "" if there's none."""
        found = INSTANCE.search(str(text).strip().casefold())
        return found.group(0) if found else ""

    async def elements(self) -> dict[str, str]:
        """His Elements on StreamElements: id → name."""
        token, channel = self._account.credentials()
        async with self._client(token) as client:
            found = _checked(await client.get(f"{API}/{channel}")).json()
        instances = [entry.get("widgetInstance") or {} for entry in found if isinstance(entry, dict)]
        return {str(i["widgetInstanceId"]): str(i.get("displayName") or i["widgetInstanceId"])
                for i in instances if i.get("widgetInstanceId")}

    async def fetch(self, text: str) -> tuple[str, dict[str, Any]]:
        """(its name, its settings as published) for the Element he pasted or picked."""
        instance = self.instance_id(text)
        if not instance:
            raise ValueError("That's not a StreamElements Element: paste its address from the editor, like "
                             "https://widgets.streamelements.com/widgets/editor/…/…")
        token, channel = self._account.credentials()
        async with self._client(token) as client:
            answer = await client.get(f"{API}/{channel}/{instance}")
            if answer.status_code == 404:
                raise KeyError("StreamElements has no such Element on your account")
            about = _checked(answer).json().get("widgetInstance") or {}
            versions = _checked(await client.get(f"{API}/{channel}/{instance}/config-version")).json()
        published = about.get("widgetInstancePublishedConfigVersionId")
        version = next((v for v in versions if v.get("widgetInstanceConfigVersionId") == published),
                       versions[0] if versions else None)
        if version is None:
            raise KeyError("That Element has no settings yet: save it once in StreamElements' editor")
        config = version.get("configData")
        return str(about.get("displayName") or instance), json.loads(config) if isinstance(config, str) else config

    async def bring(self, text: str, store: WidgetStore) -> tuple[Widget, list[str]]:
        """Imports the Element as a widget into the store, with its files. Gives the widget and the addresses
        of files that couldn't be fetched (those stay as they were in its settings)."""
        title, config = await self.fetch(text)
        config, files, missed = await self._with_local_files(config)
        name = _free(_slug(title) or "element", {taken.casefold() for taken in store.names()})
        widget = Widget(name, HTML, "", JS.format(config=json.dumps(config, indent=1, ensure_ascii=False)))
        store.save(widget)
        for file, content in files.items():
            store.save_media(name, file, content)
        return widget, missed

    async def _with_local_files(self, config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, bytes], list[str]]:
        """The settings with every file the page uses fetched: (settings naming the local files, file → its
        content, addresses that failed). Of a video only the webm is taken (the .mov beside it is for Safari),
        a placeholder picture not at all."""
        config = copy.deepcopy(config)
        files: dict[str, bytes] = {}
        local: dict[str, str] = {}  # address → its file here; "" = it failed
        async with web_client(self._transport, timeout=120, follow_redirects=True,
                                     headers=BROWSER) as client:
            for state in config.get("configStates", []):
                for field in (state.get("settings") or {}).get("compositeFields", {}).values():
                    field["media"] = _used(field)
                    for media in field["media"]:
                        href = str(media.get("href") or "")
                        if media.get("role") == "font-face":
                            href = _font_address(href, field)
                        if href not in local:
                            fetch = self._font if media.get("role") == "font-face" else self._file
                            local[href] = await fetch(client, href, files)
                        if local[href]:
                            media["href"] = local[href]
        return config, files, sorted(href for href, file in local.items() if not file)

    @staticmethod
    async def _file(client: httpx.AsyncClient, href: str, files: dict[str, bytes]) -> str:
        try:
            answer = await client.get(href)
            answer.raise_for_status()
        except (httpx.HTTPError, ValueError):
            return ""
        file = _file_name(href)
        files[file] = answer.content
        return file

    async def _font(self, client: httpx.AsyncClient, href: str, files: dict[str, bytes]) -> str:
        """A font's style sheet with the font files it names: the sheet is rewritten to name the local ones."""
        try:
            answer = await client.get(href)
            if answer.status_code == 400 and ":wght@" in href:  # the font has no bold: take what it has
                answer = await client.get(href.split(":wght@")[0])
            answer.raise_for_status()
        except (httpx.HTTPError, ValueError):
            return ""
        sheet = answer.text
        for address in sorted(set(FONT_URL.findall(sheet))):
            file = await self._file(client, address, files)
            if file:
                sheet = sheet.replace(address, file)
        name = _file_name(href, ".css")
        files[name] = sheet.encode("utf-8")
        return name

    def _client(self, token: str) -> httpx.AsyncClient:
        return web_client(self._transport, timeout=20,
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})


def _checked(answer: httpx.Response) -> httpx.Response:
    if answer.status_code in (401, 403):
        raise PermissionError("StreamElements refused the token: put a fresh JWT Token into the token file "
                              "(Connections → StreamElements)")
    answer.raise_for_status()
    return answer


def _used(field: dict[str, Any]) -> list[dict[str, Any]]:
    """The files of a field that the page loads."""
    media = [m for m in field.get("media") or [] if isinstance(m, dict) and m.get("role") != "placeholder"]
    if field.get("type") == "video":
        videos = [m for m in media if str(m.get("mimeType", "")).startswith("video/")]
        return [m for m in videos if m.get("mimeType") == "video/webm"][:1] or videos[:1]
    return media


def _font_address(href: str, field: dict[str, Any]) -> str:
    """Google Fonts' address is kept without the font's name (StreamElements' page adds it): add it here."""
    if not href.startswith(GOOGLE_FONTS) or "family=" in href:
        return href
    family = str((field.get("style") or {}).get("fontFamily") or "").split(",")[0].strip(" \"'")
    return f"{GOOGLE_FONTS}?family={family.replace(' ', '+')}:wght@400;700&display=swap" if family else href


def _file_name(href: str, ending: str = "") -> str:
    """A file name of its own for an address: the same address is the same file."""
    found = ENDING.search(href.split("?")[0])
    return hashlib.sha1(href.encode("utf-8")).hexdigest()[:16] + (ending or (found.group(0).lower() if found else ""))
