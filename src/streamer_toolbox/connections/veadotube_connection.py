import asyncio
from collections.abc import Callable
from typing import Any

import websockets
from nicegui import ui

from streamer_toolbox.connections.veadotube.veadotube_actions import VeadotubeActions
from streamer_toolbox.connections.veadotube.veadotube_client import STATE_CHANGED, VeadotubeClient, url
from streamer_toolbox.connections.veadotube.veadotube_instances import VeadotubeInstances
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_base import ConnectionBase
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.gui.components.outside_link import outside_link

DOCS = "https://veado.tube/docs/tech/api/"


class VeadotubeConnection(ConnectionBase):
    """veadotube mini (PNG avatar program): its avatar's states over its websocket. The toolbox switches
    states (boxes in VeadotubeActions) and gets told when the shown state changes (`veadotube.state`, trigger
    "veadotube state changed").

    Where veadotube listens changes with every start, so it is looked up in the files veadotube keeps about
    its running programs (VeadotubeInstances); an address typed on the tab wins. It keeps trying while
    veadotube isn't running. Off until switched on."""

    id = "veadotube"
    title = "veadotube mini"
    icon = "face_retouching_natural"

    def __init__(self, settings: dict[str, Any], events: EventBus, instances: VeadotubeInstances | None = None,
                 connect: Callable[..., Any] = websockets.connect, retry_delay: float = 5.0) -> None:
        super().__init__({"address": ""}, settings)
        self._events = events
        self._instances = instances or VeadotubeInstances()
        self._connect = connect
        self._client = VeadotubeClient(self._address, self._changed, self._state, connect, retry_delay)
        self._listener: asyncio.Task | None = None

    def fields(self) -> list[SettingField]:
        return [SettingField("address", "Address",
                             hint="leave empty: the running veadotube mini is found by itself. Else like "
                                  "127.0.0.1:2424")]

    def add_gui_settings(self) -> None:
        ui.label("In veadotube mini the websocket server must be on (it is by default). The toolbox shows up "
                 "there as \"streamer-toolbox\".").classes("text-sm opacity-80")
        outside_link("veadotube's page about it", DOCS).classes("text-sm")

    async def start(self) -> None:
        await self.stop()
        self._set_status(ConnectionStatus(ConnectionState.CONNECTING, "connecting"))
        self._listener = asyncio.create_task(self._client.run())

    async def stop(self) -> None:
        if self._listener is not None:
            self._listener.cancel()
            await asyncio.gather(self._listener, return_exceptions=True)
            self._listener = None
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        """Connects once: says whether a veadotube is there. Changes nothing in it."""
        address = str(settings.get("address") or "").strip() or self._instances.address()
        if not address:
            return ConnectionStatus(ConnectionState.ERROR, "no running veadotube mini found")
        socket = None
        try:
            socket = await asyncio.wait_for(self._connect(url(address)), 5)
        except Exception as e:
            return ConnectionStatus(ConnectionState.ERROR, f"can't reach veadotube at {address} "
                                                           f"({str(e) or type(e).__name__})")
        finally:
            if socket is not None:
                await socket.close()
        return ConnectionStatus(ConnectionState.CONNECTED, "", (("Address", address),))

    def add_actions(self, actions: ActionRegistry) -> None:
        VeadotubeActions(self._client).add_to(actions)

    def _address(self) -> str:
        return str(self._settings.get("address") or "").strip() or self._instances.address()

    def _state(self, text: str) -> None:
        if text == "connected":
            self._set_status(ConnectionStatus(ConnectionState.CONNECTED, "", (("Address", self._address()),)))
        else:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, text))

    async def _changed(self, data: dict[str, Any]) -> None:
        self._events.publish(STATE_CHANGED, data)
