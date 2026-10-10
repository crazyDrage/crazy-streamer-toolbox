from nicegui import ui

from streamer_toolbox.core.events.role_loader import RoleLoader
from streamer_toolbox.core.events.role_loading import CHAT, EVERY, START, RoleLoading

MODE_TITLES = {CHAT: "Only from chat messages", START: "At toolbox start", EVERY: "Every x minutes"}
MODE_HELP = {
    CHAT: "No request at all. A viewer's role is what their last chat message said since the toolbox started; "
          "someone who didn't write yet counts as a plain viewer.",
    START: "Your mods, VIPs and subs are loaded from Twitch once, when the toolbox starts (as soon as Twitch is "
           "connected). Someone who becomes a mod later counts as one after their next chat message.",
    EVERY: "Like at toolbox start, and again every so many minutes."}
WITH_ROLE = ("A real role, told with the event: the chat triggers (Twitch, YouTube, Rumble, any platform). "
             "A role from here: Redeem, Follow, Sub, Resub, Gift subs, Cheer, Raid, Chat message deleted, "
             "StreamSocket event, the YouTube and Rumble ones with a viewer, Custom trigger. "
             "No role: Tip, StreamElements and Streamlabs activity, Tiltify, Crowd Control, Streamer.bot and Lumia "
             "events, and everything without a viewer (timer, OBS, VTube Studio, keys).")


class RoleLoadingPanel:
    """Settings → Viewer roles: when the toolbox loads who is a mod, a VIP or a sub (RoleLoading), what the
    last load gave (RoleLoader), a button to load now, and which triggers have a role at all."""

    def __init__(self, setting: RoleLoading, loader: RoleLoader) -> None:
        self._setting = setting
        self._loader = loader

    @ui.refreshable_method
    def build(self) -> None:
        setting = self._setting
        ui.label("Viewer roles").classes("text-lg font-semibold")
        ui.label("Load roles: how the toolbox knows who is a sub, a VIP or a mod, for the role checkboxes of the "
                 "triggers. Only a chat message tells a viewer's role; a redeem, a follow or a raid does not. "
                 "A trigger itself never asks Twitch.").classes("text-sm opacity-80")
        ui.toggle(MODE_TITLES, value=setting.mode, on_change=lambda e: self._set_mode(e.value)) \
            .props("no-caps unelevated")
        ui.label(MODE_HELP[setting.mode]).classes("text-sm opacity-80")
        if setting.mode == EVERY:
            ui.number("Minutes", value=setting.minutes, min=1, precision=0, step=1,
                      on_change=lambda e: self._set_minutes(e.value)).props("dense outlined").classes("w-32")
        if setting.mode != CHAT:
            ui.label("A load is 3 requests to Twitch, one more for every 100 subs, VIPs or mods above the first "
                     "100. Twitch only (YouTube and Rumble have no such lists). It needs the rights to read your "
                     "moderators and VIPs: press Connect once under Connections → Twitch.") \
                .classes("text-xs opacity-70")
            with ui.row().classes("items-center gap-3"):
                ui.button("Load now", icon="refresh", on_click=self._load_now).props("outline no-caps dense")
                ui.label(self._loader.status).classes("text-sm")
        ui.label("For the exact role of one viewer right now, a flow uses the box \"Get viewer role\".") \
            .classes("text-xs opacity-70")
        with ui.expansion("Not every trigger has a role").props("dense").classes("w-full text-sm"):
            ui.label(WITH_ROLE).classes("text-xs opacity-80")

    def _set_mode(self, mode: str) -> None:
        self._setting.set_mode(mode)
        self.build.refresh()

    def _set_minutes(self, minutes) -> None:
        if minutes:
            self._setting.set_minutes(minutes)

    async def _load_now(self) -> None:
        loaded = await self._loader.load()
        ui.notify(self._loader.status, type="positive" if loaded else "warning", multi_line=True)
        self.build.refresh()
