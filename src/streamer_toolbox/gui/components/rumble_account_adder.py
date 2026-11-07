from collections.abc import Callable
from typing import TYPE_CHECKING

from nicegui import ui

from streamer_toolbox.gui.components.account_adder import AccountAdder

if TYPE_CHECKING:
    from streamer_toolbox.connections.rumble_connection import RumbleConnection


class RumbleAccountAdder(AccountAdder):
    """Rumble's Add account: paste another Live Stream API address. The toolbox asks Rumble once with it and
    keeps it under the name Rumble gives; the address itself is never shown again."""

    def __init__(self, rumble: "RumbleConnection") -> None:
        self._rumble = rumble

    def build(self, added: Callable[[], None]) -> None:
        address = ui.input("Live Stream API address", password=True).classes("w-full") \
            .props("autocomplete=off")
        state = ui.label("").classes("text-xs opacity-70")

        async def add() -> None:
            state.set_text("asking Rumble…")
            try:
                name = await self._rumble.add_account(address.value or "")
            except Exception as e:
                state.set_text(f"not added: {e or type(e).__name__}")
                return
            address.set_value("")
            state.set_text(f"{name} is in the list")
            ui.notify(f"Rumble account {name} added", type="positive")
            added()

        ui.button("Add", icon="person_add", on_click=add).props("unelevated no-caps")
