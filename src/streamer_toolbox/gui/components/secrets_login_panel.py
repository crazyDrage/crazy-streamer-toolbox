import asyncio

from nicegui import ui

from streamer_toolbox.core.security.secret_vault import MIN_LENGTH, SecretVault


class SecretsLoginPanel:
    """Settings → Login: says what a login does, switches it on (a password, typed twice) and off again (the
    password once). The work is SecretVault's."""

    def __init__(self, vault: SecretVault, folder: str) -> None:
        self._vault = vault
        self._folder = folder

    @ui.refreshable_method
    def build(self) -> None:
        vault = self._vault
        ui.label("Login").classes("text-lg font-semibold")
        ui.label("A password for the toolbox itself. With a login, your tokens, keys and saved logins are "
                 "encrypted on this PC, and the toolbox asks for the password at every start: until you typed "
                 "it, nothing starts and nothing is connected. Without a login it starts by itself and "
                 "connects to everything, as before.").classes("text-sm opacity-80")
        ui.label("Only this folder is changed:").classes("text-sm")
        ui.label(self._folder).classes("text-sm font-mono break-all")
        ui.label("Your settings, flows, variables and everything else stay as they are. This is not the "
                 "password for other devices (Settings → Other devices): that one stays its own.") \
            .classes("text-xs opacity-70")
        if vault.active:
            ui.label("Login is on.").classes("text-sm text-positive font-medium")
            password = ui.input("Password", password=True, password_toggle_button=True) \
                .props("dense outlined autocomplete=current-password").classes("w-full")

            async def switch_off() -> None:
                if await asyncio.to_thread(vault.remove_login, password.value or ""):
                    ui.notify("Login is off. The files are plain again.", type="positive")
                    self.build.refresh()
                else:
                    password.set_value("")
                    ui.notify("Wrong password.", type="warning")

            ui.button("Switch login off", icon="lock_open", on_click=switch_off).props("outline no-caps")
        else:
            ui.label("Login is off.").classes("text-sm opacity-80")
            with ui.row().classes("items-end no-wrap gap-2 w-full"):
                first = ui.input("New password", password=True, password_toggle_button=True) \
                    .props("dense outlined autocomplete=new-password").classes("flex-1")
                again = ui.input("Again", password=True).props("dense outlined autocomplete=new-password") \
                    .classes("flex-1")

            async def switch_on() -> None:
                if len(first.value or "") < MIN_LENGTH:
                    ui.notify(f"Use at least {MIN_LENGTH} characters", type="warning")
                elif first.value != again.value:
                    ui.notify("The two passwords are not the same", type="warning")
                else:
                    await asyncio.to_thread(vault.set_login, first.value)
                    ui.notify("Login is on. The next start asks for the password.", type="positive")
                    self.build.refresh()

            ui.button("Switch login on", icon="lock", on_click=switch_on).props("unelevated no-caps")
        ui.label("A forgotten password can't be recovered: the tokens would have to be typed in again, and "
                 "Twitch and YouTube connected again.").classes("text-xs opacity-60")
