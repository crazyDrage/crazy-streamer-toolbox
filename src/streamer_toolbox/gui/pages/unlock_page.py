import asyncio
from collections.abc import Awaitable, Callable

from nicegui import ui
from starlette.requests import Request

from streamer_toolbox.core.app_name import APP_NAME
from streamer_toolbox.core.security.login_throttle import LoginThrottle
from streamer_toolbox.core.security.secret_vault import SecretVault
from streamer_toolbox.gui.components.app_shell import AppShell
from streamer_toolbox.gui.components.look import Look


class UnlockPage:
    """/unlock: the toolbox's own login (Settings → Login). Shown instead of everything else after a start
    while a login is set; the right password opens the secrets (SecretVault) and only then the toolbox
    starts its work (`start`: the connections, timers and background loads)."""

    def __init__(self, vault: SecretVault, throttle: LoginThrottle, start: Callable[[], Awaitable[None]]) -> None:
        self._vault = vault
        self._throttle = throttle
        self._start = start

    def build(self, request: Request, next: str = "/") -> None:
        Look.apply(AppShell.theme())
        address = request.client.host if request.client else "?"
        target = next if next.startswith("/") and not next.startswith(("//", "/unlock")) else "/"
        if self._vault.unlocked:
            ui.navigate.to(target)
            return
        with ui.card().classes("absolute-center w-80 max-w-[90vw] gap-3"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("construction").classes("text-2xl text-primary")
                ui.label(APP_NAME).classes("text-lg font-semibold")
            ui.label("Log in to start the toolbox. Nothing is connected until then.").classes("text-sm opacity-80")
            password = ui.input("Password", password=True, password_toggle_button=True) \
                .props("outlined autofocus").classes("w-full")
            message = ui.label("").classes("text-sm text-negative")

            async def log_in() -> None:
                wait = self._throttle.wait_seconds(address)
                if wait:
                    message.set_text(f"Too many tries. Wait {int(wait) + 1} seconds.")
                    return
                if await asyncio.to_thread(self._vault.unlock, password.value or ""):
                    self._throttle.succeeded(address)
                    await self._start()
                    ui.navigate.to(target)
                else:
                    self._throttle.failed(address)
                    password.set_value("")
                    message.set_text("Wrong password.")

            password.on("keydown.enter", log_in)
            ui.button("Log in", icon="lock_open", on_click=log_in).props("unelevated no-caps").classes("w-full")
            ui.label("Forgot it? It can't be recovered: delete the folder \"secrets\" in the settings folder, "
                     "then type your tokens in again.").classes("text-xs opacity-60")
