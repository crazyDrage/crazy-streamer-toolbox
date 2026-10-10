from typing import Any

import httpx

from streamer_toolbox.core.config.config_table_writer import ConfigTableWriter
from streamer_toolbox.core.web.web_client import web_client

API = "https://api.streamelements.com/kappa/v2"
TABLE, KEY = "widgets", "streamelements_fallback"


class StreamElementsFallback:
    """The switch "ask StreamElements when the toolbox can't answer", and the asking. Widgets' questions to
    StreamElements' public API go to the toolbox (WidgetPage rewrites the address, widget_router answers), so a
    widget works without StreamElements. Off (the start): what the toolbox can't answer stays unanswered. On:
    the toolbox itself asks StreamElements' public API (no token, read only) and hands the answer on. Kept as
    `[widgets] streamelements_fallback` in toolbox.toml."""

    def __init__(self, settings: dict[str, Any], writer: ConfigTableWriter | None = None,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._on = bool(settings.get(KEY, False))
        self._writer = writer
        self._transport = transport

    @property
    def on(self) -> bool:
        return self._on

    def set(self, on: bool) -> None:
        self._on = bool(on)
        if self._writer is not None:
            self._writer.save(TABLE, {KEY: self._on})

    async def get(self, path: str) -> Any | None:
        """StreamElements' answer to GET <their API>/<path>; None when the switch is off, they can't be reached
        or they say no."""
        if not self._on:
            return None
        try:
            async with web_client(self._transport, timeout=10) as client:
                answer = await client.get(f"{API}/{path.lstrip('/')}", headers={"Accept": "application/json"})
            return answer.json() if answer.status_code == 200 else None
        except (httpx.HTTPError, ValueError):
            return None
