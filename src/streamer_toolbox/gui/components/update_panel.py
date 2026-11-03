import logging

from nicegui import background_tasks, ui

from streamer_toolbox.core.app_version import APP_VERSION, stage
from streamer_toolbox.core.config.config_table_writer import ConfigTableWriter
from streamer_toolbox.core.system.toolbox_release import ToolboxRelease
from streamer_toolbox.core.system.toolbox_restart import ToolboxRestart
from streamer_toolbox.core.system.toolbox_update import CHANNELS, ToolboxUpdate
from streamer_toolbox.gui.components.header_notice import HeaderNotice

log = logging.getLogger(__name__)
TABLE = "update"  # toolbox.toml: [update] check = true / false


class UpdatePanel:
    """The toolbox's own update (his next release plan, part 1: "both", tell and download and install, "at the
    top"): a newer release is a button next to the toolbox's name ("Update 0.3.0", `notices`), which opens
    what's new and "Download and install". Settings → General has the version, "Look for updates once a day"
    and "Look now". A toolbox run from its code only tells (ToolboxUpdate.installable)."""

    def __init__(self, update: ToolboxUpdate, restart: ToolboxRestart, writer: ConfigTableWriter, check: bool,
                 notices: dict[str, HeaderNotice]) -> None:
        self._update = update
        self._restart = restart
        self._writer = writer
        self._check = check
        self._notices = notices
        self._said = ""  # what the last "Look now" found

    @property
    def checking(self) -> bool:
        """ "Look for updates once a day" is on (the plugin listings follow it too)."""
        return self._check

    def start(self) -> None:
        """At the toolbox's start: what the last update did, then the day's check (when it is on)."""
        result = self._update.result()
        if result and result.get("ok"):
            log.info("updated to %s", result.get("version"))
        elif result:
            self._notices["update_failed"] = HeaderNotice(
                "Update failed", f"The update to {result.get('version')} didn't work, so this is still "
                f"{APP_VERSION}:\n{result.get('error')}\n\nWhat happened is in cache/update/swap.log in the "
                "settings folder. Try again in Settings → General, or get the new version from its page.")
        self._update.clean()
        self._show(self._update.newest)
        if self._check:
            background_tasks.create(self._look(), name="update check")

    def build(self) -> None:
        ui.label("Update").classes("text-lg font-semibold")
        ui.label(f"This is version {APP_VERSION}.").classes("text-sm")
        ui.switch("Look for updates once a day", value=self._check, on_change=lambda e: self._set_check(e.value)) \
            .tooltip("One small question to GitHub a day; a new version shows next to the toolbox's name")
        ui.select(CHANNELS, value=self._update.channel, label="Which versions",
                  on_change=lambda e: self._set_channel(e.value)).props("outlined dense").classes("w-64 max-w-full")
        ui.label("Test versions (dev, alpha, beta, rc) can break things. Releases only is the normal choice.") \
            .classes("text-xs opacity-60")
        self._state()

    @ui.refreshable_method
    def _state(self) -> None:
        newest = self._update.newest
        with ui.row().classes("items-center gap-2"):
            ui.button("Look now", icon="refresh", on_click=self._look_now).props("outline no-caps")
            if newest is not None:
                ui.button(f"Update to {newest.version}", icon="system_update",
                          on_click=lambda: self.dialog(newest)).props("unelevated no-caps")
        if self._said:
            ui.label(self._said).classes("text-sm opacity-80")

    def dialog(self, release: ToolboxRelease) -> None:
        """What's new, and Download and install (or its page, for a toolbox run from its code)."""
        can_install = self._update.installable and self._restart.available and bool(release.url)
        with ui.dialog() as dialog, ui.card().classes("w-[36rem] max-w-full gap-3"):
            ui.label(f"Version {release.version} is out").classes("text-lg font-semibold")
            ui.label(f"This is {APP_VERSION}.").classes("text-sm opacity-80")
            if stage(release.version) != "release":
                ui.label(f"A test version ({stage(release.version)}): it can break things.") \
                    .classes("text-sm text-warning")
            with ui.scroll_area().classes("w-full h-64 border rounded"):
                ui.markdown(release.notes or "(no text for this release)").classes("text-sm tb-notes")
            if can_install:
                ui.label("Download and install: a copy of your settings goes into the backups folder first. Then "
                         "the toolbox stops, puts the new version in and starts again by itself (a minute or "
                         "two). Your settings stay as they are.").classes("text-sm")
            else:
                ui.label("This toolbox runs from its code: get the new version from its page.") \
                    .classes("text-sm")
            said = ui.label("").classes("text-sm text-negative whitespace-pre-line")
            spinner = ui.spinner(size="sm")
            spinner.visible = False

            async def install() -> None:
                button.disable()
                spinner.visible = True
                said.set_text("Downloading ...")
                said.classes(replace="text-sm opacity-80")
                try:
                    await self._update.prepare(release)
                except Exception as e:
                    said.set_text(f"Not installed: {e}")
                    said.classes(replace="text-sm text-negative whitespace-pre-line")
                    spinner.visible = False
                    button.enable()
                    return
                said.set_text("Installing: the toolbox stops now and comes back by itself.")
                ui.timer(0.5, lambda: self._restart.request(update=True), once=True)

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Later", on_click=dialog.close).props("flat no-caps")
                if release.page:
                    ui.button("Its page", icon="open_in_new").props(f"flat no-caps href={release.page} target=_blank")
                button = ui.button("Download and install", icon="download", on_click=install) \
                    .props("unelevated no-caps")
                button.visible = can_install
        dialog.open()

    async def _look(self) -> None:
        try:
            self._show(await self._update.check())
        except Exception as e:  # no internet, GitHub's limit: tried again tomorrow
            log.info("update check: %s", e)

    async def _look_now(self) -> None:
        try:
            newest = await self._update.check(force=True)
        except Exception as e:
            self._said = f"Couldn't ask: {e}"
        else:
            self._show(newest)
            self._said = f"Version {newest.version} is out." if newest else f"{APP_VERSION} is the newest."
        self._state.refresh()

    def _show(self, release: ToolboxRelease | None) -> None:
        if release is None:
            self._notices.pop("update", None)
            return
        self._notices["update"] = HeaderNotice(f"Update {release.version}", "", icon="system_update",
                                               on_press=lambda: self.dialog(release), color="primary")

    def _set_check(self, on: bool) -> None:
        self._check = on
        self._writer.save(TABLE, {"check": on})

    async def _set_channel(self, channel: str) -> None:
        self._update.channel = channel
        self._writer.save(TABLE, {"channel": channel})
        await self._look_now()  # what is offered changes now, not tomorrow
