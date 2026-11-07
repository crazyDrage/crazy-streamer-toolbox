import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING

from nicegui import ui

from streamer_toolbox.gui.components.account_adder import AccountAdder

if TYPE_CHECKING:
    from streamer_toolbox.connections.youtube_connection import YouTubeConnection


class YouTubeAccountAdder(AccountAdder):
    """YouTube's Add account: channel or bot account, then Google's login in a browser on this PC (Google sends
    the answer to this PC, so it can't be confirmed on a phone). Google asks which of the browser's accounts; the
    link is shown too, for another browser or a private window on this PC."""

    def __init__(self, youtube: "YouTubeConnection") -> None:
        self._youtube = youtube
        self._adding: asyncio.Task | None = None
        self._added: Callable[[], None] = lambda: None

    def build(self, added: Callable[[], None]) -> None:
        self._added = added
        kind = ui.radio({"channel": "Channel account: another channel of yours",
                         "bot": "Bot account: writes in your live chat (it asks Google for the permission to "
                                "write)"}, value="channel")
        self._box = ui.column().classes("w-full gap-1")
        with ui.row().classes("gap-2"):
            ui.button("Log in", icon="login", on_click=lambda: self._log_in("", kind.value == "bot")) \
                .props("unelevated no-caps")
            ui.button("Cancel", on_click=self._cancel).props("flat no-caps")

    def logs_in_again(self) -> bool:
        return True

    def log_in_again(self, name: str) -> None:
        self._log_in(name, self._youtube.is_bot(name))

    def _log_in(self, name: str, bot: bool) -> None:
        self._cancel()
        self._box.clear()
        with self._box:
            if name:
                ui.label(f"Log in again as {name}:").classes("text-sm font-semibold")
            ui.label("A browser tab opened on this PC: pick the Google account there and allow the app. Wrong "
                     "browser? Open this link in another browser or a private window on this PC:") \
                .classes("text-sm")
            link_row = ui.row().classes("items-center gap-2 w-full no-wrap")
            state = ui.label("opening the login…").classes("text-xs opacity-70")

        def show(page: str) -> None:
            if link_row.is_deleted:
                return
            with link_row:
                ui.label(page).classes("text-sm break-all select-all")
                ui.button(icon="content_copy", on_click=lambda: (ui.clipboard.write(page),
                                                                 ui.notify("Link copied"))) \
                    .props("flat round dense size=sm").tooltip("Copy the link")
            state.set_text("waiting… (3 minutes)")

        def say(text: str) -> None:
            if not state.is_deleted:
                state.set_text(text)

        async def wait() -> None:
            try:
                added = await self._youtube.add_account(bot, show)
            except asyncio.CancelledError:
                say("cancelled")
                raise
            except Exception as e:
                say(f"not added: {e or type(e).__name__}")
                return
            say(f"{added} is in the list" + (" (as a bot)" if bot else ""))
            if not self._box.is_deleted:
                with self._box:
                    ui.notify(f"YouTube account {added} added", type="positive")
                self._added()

        self._adding = asyncio.get_running_loop().create_task(wait())

    def _cancel(self) -> None:
        if self._adding is not None and not self._adding.done():
            self._adding.cancel()
        self._adding = None
