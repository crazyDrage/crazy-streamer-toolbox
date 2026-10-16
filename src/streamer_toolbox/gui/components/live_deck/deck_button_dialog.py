from dataclasses import replace
from urllib.parse import quote

from nicegui import ui

from streamer_toolbox.core.actions.action_description import required_and_optional_params
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.deck.deck_button import COLORS, TEXT_COLOR, DeckButton
from streamer_toolbox.core.deck.deck_images import KINDS, DeckImages
from streamer_toolbox.core.flows.flow_library import FlowLibrary

ICONS = ("play_arrow", "stop", "bolt", "star", "favorite", "celebration", "music_note", "volume_up", "videocam",
         "movie", "photo_camera", "mic", "face", "pets", "emoji_nature", "local_fire_department", "water_drop",
         "timer", "loop", "swap_horiz", "open_with", "zoom_in", "visibility", "chat", "campaign", "redeem",
         "sports_esports", "home", "desktop_windows", "vibration", "auto_awesome", "waving_hand")
DELETE = "delete"  # what open() gives when the button was deleted


class DeckButtonDialog:
    """Edits one Live deck button: what it runs (a flow or another action) with fixed values for its fields,
    its label, colour, text colour, icon or picture, and page. open() gives (button, page name), DELETE, or
    None (cancelled)."""

    def __init__(self, button: DeckButton | None, page: str, pages: list[str], actions: ActionRegistry,
                 flows: FlowLibrary, images: DeckImages) -> None:
        self._button = replace(button, params=dict(button.params)) if button else DeckButton("", "")
        self._new = button is None
        self._page = page
        self._pages = pages
        self._actions = actions
        self._flows = flows
        self._images = images

    async def open(self) -> tuple[DeckButton, str] | str | None:
        button = self._button
        with ui.dialog() as dialog, ui.card().classes("w-[560px] max-w-[96vw] gap-3"):
            ui.label("New button" if self._new else "Button").classes("text-lg font-semibold")
            ui.select(self._choices(), value=button.action or None, label="What it runs", with_input=True,
                      on_change=lambda e: self._picked(e.value, label)) \
                .props("outlined dense options-dense").classes("w-full")
            label = ui.input("Label", value=button.label,
                             on_change=lambda e: setattr(button, "label", e.value)) \
                .props("outlined dense").classes("w-full")
            self._fields()
            ui.label("Colour").classes("text-sm font-semibold")
            self._colors()
            ui.color_input("Text colour", value=button.text_color,
                           on_change=lambda e: setattr(button, "text_color", e.value or TEXT_COLOR)) \
                .props("dense outlined").classes("w-36")
            ui.label("Picture").classes("text-sm font-semibold")
            self._picture()
            ui.label("Icon (shown when there is no picture)").classes("text-sm font-semibold")
            self._icons()
            if len(self._pages) > 1:
                ui.select(self._pages, value=self._page, label="Page",
                          on_change=lambda e: setattr(self, "_page", e.value)) \
                    .props("outlined dense").classes("w-full")
            with ui.row().classes("w-full items-center gap-2 pt-2"):
                if not self._new:
                    ui.button("Delete", icon="delete", on_click=lambda: dialog.submit(DELETE)) \
                        .props("flat no-caps color=negative")
                ui.space()
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat no-caps")
                ui.button("Save", icon="check", on_click=lambda: self._save(dialog)).props("unelevated no-caps")
        result = await dialog
        if not dialog.is_deleted:
            dialog.delete()
        return result

    def _choices(self) -> dict[str, str]:
        """Flows first (what a deck button mostly runs), then the other actions."""
        flows = {f.action_name: f"Flow · {f.label}"
                 for f in sorted(self._flows.all(), key=lambda f: f.label.casefold())}
        others = {a.name: f"{a.category_title} · {a.title}" for a in self._actions.all() if a.category != "flow"}
        current = {self._button.action: self._button.action} if self._button.action and \
            self._button.action not in flows | others else {}
        return flows | dict(sorted(others.items(), key=lambda kv: kv[1].casefold())) | current

    def _picked(self, action: str | None, label: ui.input) -> None:
        old_title = self._title(self._button.action)
        self._button.action = action or ""
        self._button.params = {}
        if not self._button.label or self._button.label == old_title:
            label.set_value(self._title(self._button.action))
        self._fields.refresh()

    def _title(self, action: str) -> str:
        if not action or action not in self._actions:
            return ""
        flow = self._flows.get(action[5:]) if action.startswith("flow.") else None
        return flow.label if flow else self._actions.get(action).title

    @ui.refreshable_method
    def _fields(self) -> None:
        """The action's fields (a flow's inputs): a value here goes with every press; empty = its default, or the
        press asks for it if it has none."""
        action = self._button.action
        if not action or action not in self._actions:
            return
        params = required_and_optional_params(self._actions.get(action))
        if not params:
            return
        flow = self._flows.get(action[5:]) if action.startswith("flow.") else None
        about = {i.name: i for i in flow.inputs} if flow else {}
        ui.label("Values it sends").classes("text-sm font-semibold")
        for param in params:
            name = param["name"]
            known = about.get(name)
            hint = (known.description if known else "") or ""
            if known and known.default not in (None, ""):
                hint = f"{hint + ' · ' if hint else ''}empty = {known.default}"
            elif param["required"]:
                hint = f"{hint + ' · ' if hint else ''}empty = it asks when pressed"
            ui.input(name.replace("_", " ").capitalize(), value=str(self._button.params.get(name, "")),
                     on_change=lambda e, n=name: self._set_param(n, e.value)) \
                .props("outlined dense").classes("w-full")
            if hint:
                ui.label(hint).classes("text-xs opacity-60 -mt-2")

    def _set_param(self, name: str, value: str) -> None:
        if value.strip():
            self._button.params[name] = value
        else:
            self._button.params.pop(name, None)

    @ui.refreshable_method
    def _colors(self) -> None:
        with ui.row().classes("gap-2 items-center"):
            for color in COLORS:
                chosen = color == self._button.color
                ui.button(on_click=lambda c=color: self._set_color(c)) \
                    .props(f"round dense unelevated {'icon=check' if chosen else ''}") \
                    .style(f"background:{color} !important; color:white; width:32px; height:32px")
            ui.color_input(value=self._button.color, on_change=lambda e: self._set_color(e.value, refresh=False)) \
                .props("dense outlined").classes("w-36")

    def _set_color(self, color: str, refresh: bool = True) -> None:
        if color:
            self._button.color = color
        if refresh:
            self._colors.refresh()

    @ui.refreshable_method
    def _picture(self) -> None:
        """The button's picture: one shown with Remove and the fill switch, or a field to add one."""
        button = self._button
        if button.image:
            with ui.row().classes("items-center gap-3 w-full"):
                ui.element("div").classes("w-16 h-16 rounded").style(
                    f"background:{button.color} url('{DeckImages.url(quote(button.image))}') center / "
                    f"{'cover' if button.fill else 'contain'} no-repeat")
                with ui.column().classes("gap-1"):
                    ui.label(button.image).classes("text-xs font-mono break-all")
                    ui.switch("Fill the button (the edges may be cut)", value=button.fill,
                              on_change=lambda e: self._set_fill(e.value))
                ui.space()
                ui.button("Remove", icon="close", on_click=self._remove_picture).props("flat dense no-caps")
            return

        async def uploaded(e) -> None:
            try:
                self._button.image = self._images.add(e.file.name, await e.file.read())
            except Exception as error:
                ui.notify(f"Not added: {error}", type="negative", multi_line=True)
                return
            self._picture.refresh()

        ui.upload(on_upload=uploaded, auto_upload=True, max_files=1) \
            .props(f'accept="{",".join(KINDS)}" flat bordered dense '
                   'label="Press + to pick a picture, or drop it here"').classes("w-full")

    def _set_fill(self, fill: bool) -> None:
        self._button.fill = fill
        self._picture.refresh()

    def _remove_picture(self) -> None:
        self._button.image = ""  # the file stays in the folder: another button may show it
        self._picture.refresh()

    @ui.refreshable_method
    def _icons(self) -> None:
        with ui.element("div").classes("grid grid-cols-8 gap-1 w-full"):
            for name in ICONS:
                chosen = name == self._button.icon
                ui.button(icon=name, on_click=lambda n=name: self._set_icon(n)) \
                    .props(f"dense {'unelevated' if chosen else 'flat'}").tooltip(name)
        ui.input("or any Material icon name", value=self._button.icon,
                 on_change=lambda e: setattr(self._button, "icon", e.value.strip() or "play_arrow")) \
            .props("outlined dense").classes("w-full")

    def _set_icon(self, name: str) -> None:
        self._button.icon = name
        self._icons.refresh()

    def _save(self, dialog: ui.dialog) -> None:
        if not self._button.action:
            ui.notify("Pick what the button runs", type="warning")
            return
        if not self._button.label.strip():
            self._button.label = self._title(self._button.action) or self._button.action
        dialog.submit((self._button, self._page))
