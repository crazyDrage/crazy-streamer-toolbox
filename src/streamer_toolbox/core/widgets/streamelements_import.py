import json
import re
from pathlib import Path
from typing import Any

import httpx

from streamer_toolbox.core.web.web_client import web_client
from streamer_toolbox.core.widgets.widget import Widget
from streamer_toolbox.core.widgets.widget_store import parse_fields

API = "https://api.streamelements.com/kappa/v2/overlays"
OVERLAY_ID = re.compile(r"[0-9a-f]{24}")
FRAME_KEYS = ("width", "height", "top", "left")


class StreamElementsImport:
    """Takes the custom widgets out of one of his StreamElements overlays: asks StreamElements' API for the
    overlay (read only, with the JWT in config/streamelements_token.txt, the same file the connection uses) and
    turns every custom widget in it into a Widget: its HTML, CSS, JS, FIELDS, the values he set there, and where
    it sat on the overlay. Their built-in widgets (alert box, labels, ...) have no code to take."""

    def __init__(self, token_path: Path, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._token_path = token_path
        self._transport = transport

    @staticmethod
    def overlay_id(text: str) -> str:
        """The overlay's id from what he pasted: the editor's address, the overlay's address, or the id itself."""
        found = OVERLAY_ID.search(str(text).strip().casefold())
        if not found:
            raise ValueError("That's not a StreamElements overlay: paste its address from the overlay editor, "
                             "like https://streamelements.com/overlay/…/editor")
        return found.group(0)

    async def overlays(self) -> dict[str, str]:
        """His overlays on StreamElements: id → name, newest change first."""
        token, channel = self._token()
        async with web_client(self._transport, timeout=20) as client:
            answer = await client.get(f"{API}/{channel}", params={"limit": 100},
                                      headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
        if answer.status_code in (401, 403):
            raise PermissionError("StreamElements refused the token: put a fresh JWT Token into "
                                  f"{self._token_path}")
        answer.raise_for_status()
        found = answer.json()
        docs = found.get("docs", []) if isinstance(found, dict) else found
        docs = sorted(docs, key=lambda d: str(d.get("updatedAt") or ""), reverse=True)
        return {str(d["_id"]): str(d.get("name") or d["_id"]) for d in docs if d.get("_id")}

    async def fetch(self, text: str) -> dict[str, Any]:
        """The overlay as StreamElements has it."""
        overlay = self.overlay_id(text)
        token, channel = self._token()
        async with web_client(self._transport, timeout=20) as client:
            answer = await client.get(f"{API}/{channel}/{overlay}",
                                      headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
        if answer.status_code in (401, 403):
            raise PermissionError("StreamElements refused the token: put a fresh JWT Token into "
                                  f"{self._token_path}")
        if answer.status_code == 404:
            raise KeyError("StreamElements has no such overlay on your account")
        answer.raise_for_status()
        return answer.json()

    @staticmethod
    def widgets(overlay: dict[str, Any], taken: list[str]) -> list[Widget]:
        """The custom widgets of an overlay, each with a name that isn't in `taken` (the overlay's name, numbered
        when there are several)."""
        custom = [w for w in overlay.get("widgets", []) if isinstance(w.get("variables"), dict)
                  and any(w["variables"].get(part) for part in ("html", "js"))]
        base = _slug(str(overlay.get("name") or "")) or "streamelements"
        used = {name.casefold() for name in taken}
        widgets = []
        for number, found in enumerate(custom, 1):
            variables = found["variables"]
            name = _free(base if len(custom) == 1 else f"{base}_{number}", used)
            used.add(name.casefold())
            fields = variables.get("fields") or {}
            values = variables.get("fieldData")
            css = found.get("css") or {}
            widgets.append(Widget(
                name, str(variables.get("html") or ""), str(variables.get("css") or ""),
                str(variables.get("js") or ""),
                fields if isinstance(fields, dict) else parse_fields(str(fields)),
                values if isinstance(values, dict) else {},
                {key: css[key] for key in FRAME_KEYS if key in css}))
        return widgets

    def account_id(self) -> str:
        """His StreamElements account id (line 2 of the token file, else the one inside the JWT), "" if there is
        no token. Widgets get it as channel.id: some ask StreamElements' public API about the channel with it."""
        try:
            return self._token()[1]
        except PermissionError:
            return ""

    def credentials(self) -> tuple[str, str]:
        """(his JWT, his account id) for StreamElements' API; PermissionError says what is missing."""
        return self._token()

    def _token(self) -> tuple[str, str]:
        text = self._token_path.read_text(encoding="utf-8") if self._token_path.is_file() else ""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            raise PermissionError(f"No token yet: put your StreamElements JWT Token into {self._token_path}")
        channel = lines[1] if len(lines) > 1 else _channel_in(lines[0])
        if not channel:
            raise PermissionError(f"Put your StreamElements Account ID on line 2 of {self._token_path}")
        return lines[0], channel


def _slug(text: str) -> str:
    """A widget name from an overlay's name: "Next Activity!" → "next_activity"."""
    return re.sub(r"[^a-z0-9]+", "_", text.casefold()).strip("_")


def _free(name: str, used: set[str]) -> str:
    candidate, number = name, 2
    while candidate.casefold() in used:
        candidate, number = f"{name}_{number}", number + 1
    return candidate


def _channel_in(token: str) -> str:
    import base64
    try:
        part = token.split(".")[1]
        return str(json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))).get("channel") or "")
    except (IndexError, ValueError):
        return ""
