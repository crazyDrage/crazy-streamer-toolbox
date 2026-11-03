from typing import Any, Callable

import httpx
from nicegui import ui

from streamer_toolbox.connections.sammi.boxes.change_sammi_button import ChangeSammiButton
from streamer_toolbox.connections.sammi.boxes.deck_on_off import DeckOnOff
from streamer_toolbox.connections.sammi.boxes.get_decks import GetDecks
from streamer_toolbox.connections.sammi.boxes.get_sammi_variable import GetSammiVariable
from streamer_toolbox.connections.sammi.boxes.is_deck_on import IsDeckOn
from streamer_toolbox.connections.sammi.boxes.press_sammi_button import PressSammiButton
from streamer_toolbox.connections.sammi.boxes.release_sammi_button import ReleaseSammiButton
from streamer_toolbox.connections.sammi.boxes.sammi_alert import SammiAlert
from streamer_toolbox.connections.sammi.boxes.sammi_notification import SammiNotification
from streamer_toolbox.connections.sammi.boxes.sammi_popup import SammiPopup
from streamer_toolbox.connections.sammi.boxes.set_sammi_variable import SetSammiVariable
from streamer_toolbox.connections.sammi.sammi_deck_list import SammiDeckList
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_base import ConnectionBase
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.web.web_client import web_client


class SammiConnection(ConnectionBase):
    """SAMMI's Local API (sammi.solutions/docs/api/reference). SAMMI calls the toolbox with HTTP Request buttons;
    this is the other way round: the toolbox pressing SAMMI buttons and setting SAMMI variables."""

    id = "sammi"
    title = "SAMMI"
    icon = "dashboard_customize"
    retry_when_down = True

    def __init__(self, settings: dict[str, Any], deck: Callable[[], tuple[str, int]],
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        super().__init__({"url": "http://127.0.0.1:9450", "password": ""}, settings)
        self._deck = deck  # the toolbox deck to paste into SAMMI (Copy deck)
        self._transport = transport
        self._decks = SammiDeckList(lambda: self.get(request="getDeckList"))  # SAMMI's own decks and buttons

    def fields(self) -> list[SettingField]:
        return [SettingField("url", "Address", hint="SAMMI → Settings → Local API (port 9450)"),
                SettingField("password", "Password", secret=True, hint="Only if you set one in SAMMI")]

    async def start(self) -> None:
        self._set_status(await self.test(self._settings))

    async def stop(self) -> None:
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        try:
            await self._request(settings, "GET", params={"request": "getVariable", "name": "Architecture"})
        except Exception as e:
            return ConnectionStatus(ConnectionState.ERROR, _reason(e))
        return ConnectionStatus(ConnectionState.CONNECTED, "", (
            ("SAMMI API", settings["url"]),
            ("Password", "set" if settings["password"] else "none (anyone on your network can use it)"),
        ))

    async def send(self, body: dict[str, Any]) -> Any:
        """POST a Local API request, e.g. {"request": "triggerButton", "buttonID": "ID19"}."""
        return await self._call("POST", json=body)

    async def get(self, **params: Any) -> Any:
        """GET a Local API request, e.g. get(request="getDeckList")."""
        return await self._call("GET", params=params)

    async def _call(self, method: str, **kwargs: Any) -> Any:
        if not self._settings["enabled"]:
            raise NotConnectedError("SAMMI is switched off under Connections → SAMMI")
        try:
            result = await self._request(self._settings, method, **kwargs)
        except Exception as e:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, _reason(e)))
            raise
        if not self.status.ok:
            await self.start()
        return result

    @property
    def decks(self) -> SammiDeckList:
        """SAMMI's own decks and buttons (its boxes' pickers read them)."""
        return self._decks

    def add_actions(self, actions: ActionRegistry) -> None:
        for box in (SammiPopup(self), SammiAlert(self), SammiNotification(self), PressSammiButton(self),
                    ReleaseSammiButton(self), ChangeSammiButton(self), SetSammiVariable(self), GetSammiVariable(self),
                    DeckOnOff(self), IsDeckOn(self), GetDecks(self)):
            actions.add_box(box, "sammi")

    def add_gui_settings(self) -> None:
        _, count = self._deck()
        ui.label("Toolbox deck").classes("text-sm font-semibold pt-2")
        ui.label(f"One SAMMI button per toolbox action ({count}). Copy it, then use Paste Deck in SAMMI.") \
            .classes("text-sm opacity-80")
        with ui.row().classes("gap-2"):
            ui.button("Copy deck", icon="content_copy", on_click=self._copy_deck).props("no-caps unelevated")
            ui.button("Download deck file", icon="download", on_click=self._download_deck).props("no-caps outline")

    def _copy_deck(self) -> None:
        text, count = self._deck()
        ui.clipboard.write(text)
        ui.notify(f"Deck with {count} buttons copied", type="positive")

    def _download_deck(self) -> None:
        text, _ = self._deck()
        ui.download.content(text, "sammi_toolbox_deck.json", "application/json")

    async def _request(self, settings: dict[str, Any], method: str, **kwargs: Any) -> Any:
        headers = {"Authorization": settings["password"]} if settings["password"] else {}
        async with web_client(self._transport, timeout=5) as client:
            response = await client.request(method, settings["url"].rstrip("/") + "/api", headers=headers, **kwargs)
        response.raise_for_status()
        return response.json().get("data")


def _reason(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 401:
        return "SAMMI wants a password (or the password is wrong)"
    if isinstance(e, httpx.ConnectError):
        return "can't reach SAMMI: is it running, with the Local API on?"
    return str(e) or type(e).__name__
