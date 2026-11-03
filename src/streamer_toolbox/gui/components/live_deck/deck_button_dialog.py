from collections.abc import Callable
from dataclasses import replace
from urllib.parse import quote

from nicegui import ui

from streamer_toolbox.core.actions.action_description import required_and_optional_params
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.deck.deck_button import COLORS, GO_TO_PAGE, PAGE_ICON, TEXT_COLOR, DeckButton
from streamer_toolbox.core.deck.deck_images import KINDS, DeckImages
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.gui.components.flow_editor.action_picker import ActionPicker

ICONS = ("play_arrow", "stop", "bolt", "star", "favorite", "celebration", "music_note", "volume_up", "videocam",
         "movie", "photo_camera", "mic", "face", "pets", "emoji_nature", "local_fire_department", "water_drop",
         "timer", "loop", "swap_horiz", "open_with", "zoom_in", "visibility", "chat", "campaign", "redeem",
         "sports_esports", "home", "desktop_windows", "vibration", "auto_awesome", "waving_hand", "arrow_back",
         "arrow_forward")
DELETE = "delete"  # what open() gives when the button was deleted


class DeckButtonDialog:
    """Edits one Live deck button: what it does (runs a box, picked in the same window as the flow editor's
    Add box, with fixed values for its fields; or shows another page of the deck, like his SAMMI buttons; his
    round 63), its label, colour, text colour, icon or picture, and page. open() gives (button, page name),
    DELETE, or None (cancelled)."""

    def __init__(self, button: DeckButton | None, page: str, pages: list[str], actions: ActionRegistry,
                 flows: FlowLibrary, images: DeckImages, picker: Callable[[], ActionPicker]) -> None:
        self._button = replace(button, params=dict(button.params)) if button else DeckButton("", "")
        self._new = button is None
        self._page = page
        self._pages = pages
        self._actions = actions
        self._flows = flows
        self._images = images
        self._picker = picker

    async def open(self) -> tuple[DeckButton, str] | str | None:
        button = self._button
        with ui.dialog() as dialog, ui.card().classes("w-[560px] max-w-[96vw] gap-3"):
            ui.label("New button" if self._new else "Button").classes("text-lg font-semibold")
            self._what()
            self._label = ui.input("Label", value=button.label,
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

    @ui.refreshable_method
    def _what(self) -> None:
        """What a press does: run a box or show another page."""
        going = self._button.action == GO_TO_PAGE
        ui.toggle({"box": "Runs a box", "page": "Goes to a page"}, value="page" if going else "box",
                  on_change=lambda e: self._set_kind(e.value)).props("no-caps dense unelevated")
        if going:
            ui.select(self._pages, value=self._button.params.get("page"), label="Page it shows",
                      on_change=lambda e: self._set(GO_TO_PAGE, {"page": e.value} if e.value else {})) \
                .props("outlined dense").classes("w-full")
            return
        action = self._button.action
        known = self._actions.get(action) if action in self._actions else None
        with ui.row().classes("w-full items-center no-wrap gap-2"):
            with ui.column().classes("flex-1 min-w-0 gap-0"):
                ui.label(f"{known.category_title} · {self._title(action)}" if known else
                         f"{action} isn't there anymore" if action else "Nothing yet") \
                    .classes("font-medium" if known else "opacity-60")
                if known and known.description:
                    ui.label(known.description).classes("text-xs opacity-60")
            ui.button("Change" if action else "Choose", icon="search", on_click=self._choose) \
                .props("outline dense no-caps").classes("px-2 shrink-0")

    async def _choose(self) -> None:
        name = await self._picker().pick("What the button runs")
        if name:
            self._set(name, {})

    def _set_kind(self, kind: str) -> None:
        if (kind == "page") == (self._button.action == GO_TO_PAGE):
            return
        if kind == "page" and self._button.icon == DeckButton("", "").icon:
            self._button.icon = PAGE_ICON
            self._icons.refresh()
        self._set(GO_TO_PAGE if kind == "page" else "", {})

    def _set(self, action: str, params: dict[str, str]) -> None:
        """What it does changed; a label that was the old one's name follows."""
        old_title = self._title(self._button.action)
        self._button.action = action
        self._button.params = params
        if not self._button.label or self._button.label == old_title:
            self._label.set_value(self._title(action))
        self._what.refresh()
        self._fields.refresh()

    def _title(self, action: str) -> str:
        if action == GO_TO_PAGE:
            return self._button.params.get("page", "")
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
        if self._button.action == GO_TO_PAGE and not self._button.params.get("page"):
            ui.notify("Pick the page it shows", type="warning")
            return
        if not self._button.label.strip():
            self._button.label = self._title(self._button.action) or self._button.action
        dialog.submit((self._button, self._page))
