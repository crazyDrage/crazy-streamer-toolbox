from typing import Any, Callable

import httpx
from nicegui import ui

from streamer_toolbox.connections.sammi.sammi_deck_list import SammiDeckList
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_base import ConnectionBase
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.core.connections.setting_field import SettingField


DECK_STATES = {"on": 1, "off": 0, "toggle": 2}  # changeDeckStatus

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

    def add_actions(self, actions: ActionRegistry) -> None:
        decks = self._decks

        async def buttons() -> dict[str, dict[str, str]]:
            return await decks.button_groups()

        async def buttons_and_global() -> dict[str, dict[str, str]]:
            return {"(global)": {"global": "global (not a button)"}} | await decks.button_groups()

        async def deck_names() -> dict[str, str]:
            return await decks.deck_choices()

        async def deck_states() -> list[str]:
            return list(DECK_STATES)

        async def trigger_button(button_id: str) -> Any:
            return await self.send({"request": "triggerButton", "buttonID": button_id})

        async def release_button(button_id: str) -> Any:
            return await self.send({"request": "releaseButton", "buttonID": button_id})

        async def set_variable(name: str, value: str, button_id: str = "global") -> Any:
            return await self.send({"request": "setVariable", "name": name, "value": value, "buttonID": button_id})

        async def get_variable(name: str, button_id: str = "global") -> Any:
            params = {"request": "getVariable", "name": name}
            if button_id and button_id != "global":
                params["buttonID"] = button_id
            return await self.get(**params)

        async def set_deck(deck: str, state: str = "on") -> Any:
            if state not in DECK_STATES:
                raise ValueError(f"state must be one of {', '.join(DECK_STATES)}, got {state!r}")
            return await self.send({"request": "changeDeckStatus", "deckID": deck, "status": DECK_STATES[state]})

        async def get_deck_on(deck: str) -> bool:
            return bool(await self.get(request="getDeckStatus", deckID=deck))

        async def modify_button(button_id: str, text: str = "", color: str = "") -> Any:
            body: dict[str, Any] = {"request": "modifyButton", "buttonID": button_id}
            if text:
                body["text"] = text
            if color:
                body["color"] = _bgr(color)
            return await self.send(body)

        async def get_decks() -> list[dict[str, Any]]:
            return await decks.summary()

        async def popup(message: str) -> Any:
            return await self.send({"request": "popupMessage", "message": message})

        async def alert(message: str) -> Any:
            return await self.send({"request": "alertMessage", "message": message})

        async def notification(message: str, title: str = "streamer-toolbox") -> Any:
            return await self.send({"request": "notificationMessage", "title": title, "message": message})

        actions.add("sammi.popup", popup, "Shows a popup message in SAMMI", "SAMMI popup", group="Messages")
        actions.add("sammi.alert", alert, "Shows a yellow alert message in SAMMI", "SAMMI alert", group="Messages")
        actions.add("sammi.notification", notification, "Shows a bubble notification from SAMMI (like its timer "
                    "buttons do)", "SAMMI notification", group="Messages")
        actions.add("sammi.trigger_button", trigger_button, "Presses a SAMMI button (the list is read from SAMMI "
                    "each time; pick a deck first to narrow it)", "Press SAMMI button", group="Buttons",
                    options={"button_id": buttons})
        actions.add("sammi.release_button", release_button, "Releases a SAMMI button that is running (stops it)",
                    "Release SAMMI button", group="Buttons", options={"button_id": buttons})
        actions.add("sammi.modify_button", modify_button, "Changes a SAMMI button's text and / or colour "
                    "(#rrggbb); empty = keep", "Change SAMMI button", group="Buttons", options={"button_id": buttons})
        actions.add("sammi.set_variable", set_variable, "Sets a SAMMI variable (global unless a button is picked)",
                    "Set SAMMI variable", group="Variables", options={"button_id": buttons_and_global})
        actions.add("sammi.get_variable", get_variable, "Reads a SAMMI variable (global unless a button is picked)",
                    "Get SAMMI variable", group="Variables", options={"button_id": buttons_and_global})
        actions.add("sammi.set_deck", set_deck, "Switches a SAMMI deck on, off or the other way (toggle)",
                    "Deck on / off", group="Decks", options={"deck": deck_names, "state": deck_states})
        actions.add("sammi.get_deck_on", get_deck_on, "Whether a SAMMI deck is on", "Is deck on?",
                    group="Decks", options={"deck": deck_names})
        actions.add("sammi.get_decks", get_decks, "Every SAMMI deck with its buttons (name, id, on/off, buttons)",
                    "Get decks", group="Decks", live=True)

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
        async with httpx.AsyncClient(transport=self._transport, timeout=5) as client:
            response = await client.request(method, settings["url"].rstrip("/") + "/api", headers=headers, **kwargs)
        response.raise_for_status()
        return response.json().get("data")


def _bgr(color: str) -> int:
    """#rrggbb (or rrggbb) to the decimal BGR number SAMMI wants."""
    text = str(color).strip().lstrip("#")
    if len(text) != 6 or any(c not in "0123456789abcdefABCDEF" for c in text):
        raise ValueError(f"colour {color!r}: use #rrggbb, e.g. #ff8800")
    r, g, b = int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)
    return b * 65536 + g * 256 + r


def _reason(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 401:
        return "SAMMI wants a password (or the password is wrong)"
    if isinstance(e, httpx.ConnectError):
        return "can't reach SAMMI: is it running, with the Local API on?"
    return str(e) or type(e).__name__
