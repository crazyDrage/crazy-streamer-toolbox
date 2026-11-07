from nicegui import ui

from streamer_toolbox.core.interfaces.account_holder import AccountHolder
from streamer_toolbox.gui.components.account_adder import AccountAdder


class AccountsPanel:
    """The accounts part of a streaming platform's tab (his plan of 2026-11-05, docs/PLAN_multi_accounts.md; for
    every platform since 2026-11-06): the main account (drop-down), the Multiple accounts switch, the list of
    accounts (bot or channel, connected or why not, Listen to its channel, Log in again, Remove) and
    Add account, which is the platform's own (an AccountAdder)."""

    def __init__(self, holder: AccountHolder, adder: AccountAdder) -> None:
        self._holder = holder
        self._adder = adder

    def build(self) -> None:
        ui.separator()
        ui.label("Accounts").classes("font-semibold")
        self._list()
        with ui.expansion("Add account", icon="person_add").classes("w-full"):
            self._adder.build(self._list.refresh)
        shown = {"seen": self._seen()}

        def follow() -> None:  # Connect with another account, a login that stopped working, ...
            if shown["seen"] != self._seen():
                shown["seen"] = self._seen()
                self._list.refresh()

        ui.timer(2.0, follow)

    def _seen(self) -> tuple:
        holder = self._holder
        return (holder.main_account(), holder.multiple_accounts,
                tuple((n, holder.is_bot(n), holder.listens(n), holder.account_state(n))
                      for n in holder.account_names()))

    @ui.refreshable
    def _list(self) -> None:
        holder = self._holder
        names = holder.account_names()
        if not names:
            ui.label("No account yet: press Connect above, or Add account below.").classes("text-sm opacity-70")
            return
        main = holder.main_account()
        with ui.row().classes("items-center gap-3 w-full"):
            ui.select(names, value=main, label="Main account",
                      on_change=lambda e: self._set_main(e.value)).classes("min-w-[14rem]")
            ui.label("Used wherever no account is picked.").classes("text-xs opacity-60")
        ui.switch("Multiple accounts", value=holder.multiple_accounts,
                  on_change=lambda e: holder.set_multiple_accounts(e.value))
        ui.label(f'On: {holder.title} boxes and triggers get an "Account" field (empty = the main account).') \
            .classes("text-xs opacity-60 -mt-2")
        for name in names:
            self._row(name, main)

    def _row(self, name: str, main: str) -> None:
        holder = self._holder
        bot = holder.is_bot(name)
        with ui.card().classes("w-full gap-1 p-2").props("flat bordered"):
            with ui.row().classes("items-center gap-2 w-full"):
                ui.icon("smart_toy" if bot else "live_tv").classes("opacity-70")
                ui.label(name).classes("font-medium")
                if name == main:
                    ui.badge("main", color="primary")
                if holder.has_bots():
                    ui.badge("bot" if bot else "channel", color="grey")
                ui.space()
                if self._adder.logs_in_again():
                    ui.button("Log in again", icon="login", on_click=lambda: self._adder.log_in_again(name)) \
                        .props("flat dense no-caps size=sm")
                ui.button(icon="delete", on_click=lambda: self._remove(name)) \
                    .props("flat dense round size=sm color=grey").tooltip("Remove this account")
            state = holder.account_state(name)
            if state:
                ui.label(state).classes("text-xs " + ("text-positive" if state == "connected" else "text-negative"))
            if name != main and not bot:
                ui.switch("Listen to its channel", value=holder.listens(name),
                          on_change=lambda e: holder.set_listening(name, e.value)).props("dense")

    async def _remove(self, name: str) -> None:
        main = name == self._holder.main_account()
        with ui.dialog() as dialog, ui.card().classes("w-[30rem] max-w-full gap-3"):
            ui.label(f"Remove {name}?").classes("text-lg font-semibold")
            ui.label(f"This deletes the toolbox's login of {name} ({self._holder.where_kept(name)}). The account "
                     f"on {self._holder.title} stays as it is; you can add it again later.").classes("text-sm")
            ui.label("Boxes and triggers that name it say the account is missing until you add it again.") \
                .classes("text-sm opacity-80")
            if main:
                ui.label("It is the main account: another account becomes the main one, or none is left.") \
                    .classes("text-sm text-warning")
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=lambda: dialog.submit(False)).props("flat no-caps")
                ui.button("Remove", icon="delete", color="negative",
                          on_click=lambda: dialog.submit(True)).props("unelevated no-caps")
        sure = await dialog
        dialog.delete()
        if sure:
            await self._holder.remove_account(name)
            ui.notify(f"{name} removed")
            self._list.refresh()

    async def _set_main(self, name: str) -> None:
        if name and name != self._holder.main_account():
            await self._holder.set_main_account(name)
            ui.notify(f"{name} is the main account")
            self._list.refresh()
