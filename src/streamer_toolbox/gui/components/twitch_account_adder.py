import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING

from nicegui import ui

from streamer_toolbox.gui.components.account_adder import AccountAdder

if TYPE_CHECKING:
    from streamer_toolbox.connections.twitch_connection import TwitchConnection


class TwitchAccountAdder(AccountAdder):
    """Twitch's Add account (his plan of 2026-11-05, step 2): channel or bot account, then a link with a Copy
    button and the code, to open in any browser where the other account is logged in (nothing opens on this PC).
    Log in again does the same for one account."""

    def __init__(self, twitch: "TwitchConnection") -> None:
        self._twitch = twitch
        self._adding: asyncio.Task | None = None
        self._added: Callable[[], None] = lambda: None

    def build(self, added: Callable[[], None]) -> None:
        self._added = added
        kind = ui.radio({"channel": "Channel account: everything the main account may (a second channel "
                                    "of yours)",
                         "bot": "Bot account: writes in your chat, and does shoutouts, announcements, "
                                "timeouts if it's a mod in your channel"}, value="channel")
        self._box = ui.column().classes("w-full gap-1")
        with ui.row().classes("gap-2"):
            ui.button("Get the link", icon="link", on_click=lambda: self._log_in("", kind.value == "bot")) \
                .props("unelevated no-caps")
            ui.button("Cancel", on_click=self._cancel).props("flat no-caps")

    def logs_in_again(self) -> bool:
        return True

    def log_in_again(self, name: str) -> None:
        self._log_in(name, self._twitch.is_bot(name))

    def _log_in(self, name: str, bot: bool) -> None:
        """Add account, or Log in again for one: a link and a code, waited for in the background."""
        self._cancel()
        self._box.clear()
        with self._box:
            if name:
                ui.label(f"Log in again as {name}:").classes("text-sm font-semibold")
            ui.label("Open this link where that account is logged in (another browser, a private window, your "
                     "phone) and confirm the code:").classes("text-sm")
            link_row = ui.row().classes("items-center gap-2 w-full no-wrap")
            code = ui.label("").classes("text-sm font-mono")
            state = ui.label("asking Twitch for a code…").classes("text-xs opacity-70")

        def show(page: str, user_code: str) -> None:
            if link_row.is_deleted:
                return
            with link_row:
                ui.label(page).classes("text-sm break-all select-all")
                ui.button(icon="content_copy", on_click=lambda: (ui.clipboard.write(page),
                                                                 ui.notify("Link copied"))) \
                    .props("flat round dense size=sm").tooltip("Copy the link")
            code.set_text(f"Code: {user_code}")
            state.set_text("waiting… (the link works for 30 minutes)")

        def say(text: str) -> None:  # a newer Get the link (or a closed page) may have removed the label already
            if not state.is_deleted:
                state.set_text(text)

        async def wait() -> None:
            try:
                added = await self._twitch.add_account(bot, show)
            except asyncio.CancelledError:
                say("cancelled")
                raise
            except Exception as e:
                say(f"not added: {e or type(e).__name__}")
                return
            say(f"{added} is in the list" + (" (as a bot)" if bot else ""))
            if not self._box.is_deleted:
                with self._box:  # this task has no page of its own: notify on the panel's page
                    ui.notify(f"Twitch account {added} added", type="positive")
                self._added()

        self._adding = asyncio.get_running_loop().create_task(wait())

    def _cancel(self) -> None:
        if self._adding is not None and not self._adding.done():
            self._adding.cancel()
        self._adding = None
