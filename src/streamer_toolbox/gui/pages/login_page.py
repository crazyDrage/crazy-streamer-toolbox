import asyncio

from nicegui import ui
from starlette.requests import Request

from streamer_toolbox.core.security.login_throttle import LoginThrottle
from streamer_toolbox.core.security.remote_access import RemoteAccess
from streamer_toolbox.core.security.signed_in_devices import SignedInDevices
from streamer_toolbox.gui.components.app_shell import PRIMARY, THEMES, AppShell


class LoginPage:
    """/login: the password for opening the toolbox from another device (this PC never needs it)."""

    def __init__(self, access: RemoteAccess, throttle: LoginThrottle, devices: SignedInDevices) -> None:
        self._access = access
        self._throttle = throttle
        self._devices = devices

    def build(self, request: Request, next: str = "/") -> None:
        ui.dark_mode(THEMES.get(AppShell.theme()))
        ui.colors(primary=PRIMARY)
        address = request.client.host if request.client else "?"
        browser = request.session.get("id") if "session" in request.scope else None  # signed session cookie
        target = next if next.startswith("/") and not next.startswith("//") else "/"
        with ui.card().classes("absolute-center w-80 max-w-[90vw] gap-3"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("construction").classes("text-2xl text-primary")
                ui.label("streamer-toolbox").classes("text-lg font-semibold")
            if not self._access.has_password:
                ui.label("No password is set yet. Set one on the stream PC: Settings → Other devices.") \
                    .classes("text-sm")
                return
            password = ui.input("Password", password=True, password_toggle_button=True) \
                .props("outlined autofocus").classes("w-full")
            message = ui.label("").classes("text-sm text-negative")

            async def sign_in() -> None:
                wait = self._throttle.wait_seconds(address)
                if wait:
                    message.set_text(f"Too many tries. Wait {int(wait) + 1} seconds.")
                    return
                if await asyncio.to_thread(self._access.check, password.value or ""):
                    self._throttle.succeeded(address)
                    if browser:
                        self._devices.add(browser, self._access.session_key())
                    ui.navigate.to(target)
                else:
                    self._throttle.failed(address)
                    password.set_value("")
                    message.set_text("Wrong password.")

            password.on("keydown.enter", sign_in)
            ui.button("Sign in", icon="login", on_click=sign_in).props("unelevated no-caps").classes("w-full")
