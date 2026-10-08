from nicegui import ui

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.box_filter import GENERAL, BoxFilter
from streamer_toolbox.core.actions.box_filter_draft import BoxFilterDraft
from streamer_toolbox.core.actions.box_filter_store import BoxFilterStore
from streamer_toolbox.core.actions.registered_action import RegisteredAction
from streamer_toolbox.gui.components.flow_editor.action_catalog import ActionCatalog


class BoxFilterDialog:
    """One box filter, edited like the Add box window in two halves: left every box (search, categories, sub
    groups), right what's in the filter. A click on a box moves it to the other side; a heading's button moves
    its whole category or group (a whole one also takes in boxes that come later). Save writes it to the store."""

    def __init__(self, filters: BoxFilterStore, actions: ActionRegistry, old: BoxFilter | None = None) -> None:
        self._filters = filters
        self._actions = actions
        self._old = old
        self._draft = BoxFilterDraft(old)
        self._catalog = ActionCatalog(actions)
        self._category = next(iter(self._catalog.categories()), ("", "", 0))[0]
        self._search = ""

    async def open(self) -> bool:
        """True if the filter was saved."""
        with ui.dialog() as dialog, ui.card().classes("w-[76rem] max-w-full h-[88vh] gap-2 p-3"):
            self._dialog = dialog
            with ui.row().classes("items-center w-full no-wrap gap-2"):
                ui.label("Edit filter" if self._old else "New filter").classes("text-lg font-semibold shrink-0")
                self._name = ui.input(placeholder="Name, e.g. Alerts", value=self._old.name if self._old else "") \
                    .props("outlined dense autofocus").classes("flex-1 min-w-0")
                ui.button("Cancel", on_click=lambda: dialog.submit(False)).props("flat no-caps")
                ui.button("Save", icon="save", on_click=self._save).props("unelevated no-caps")
            with ui.element("div").classes("flex flex-col md:flex-row w-full flex-1 min-h-0 gap-3"):
                with ui.column().classes("flex-1 min-h-0 min-w-0 gap-1"):
                    search = ui.input(placeholder="All boxes: search, e.g. scene, volume, hotkey") \
                        .props("clearable dense outlined debounce=150").classes("w-full")
                    search.on_value_change(lambda e: self._searched(e.value or ""))
                    with ui.element("div").classes("flex flex-row w-full flex-1 min-h-0 gap-2"):
                        with ui.element("div").classes("flex flex-col gap-1 overflow-y-auto shrink-0 w-40 "
                                                       "max-h-full pr-2 border-r border-gray-500/30"):
                            self._categories()
                        with ui.element("div").classes("flex-1 min-h-0 min-w-0 max-h-full overflow-y-auto"):
                            self._available()
                with ui.column().classes("flex-1 min-h-0 min-w-0 gap-1 md:pl-3 md:border-l border-gray-500/30"):
                    self._count()
                    with ui.element("div").classes("flex-1 min-h-0 w-full max-h-full overflow-y-auto"):
                        self._chosen()
        saved = await dialog
        dialog.delete()
        return bool(saved)

    @ui.refreshable_method
    def _categories(self) -> None:
        for category, title, count in self._catalog.categories():
            chosen = not self._search and category == self._category
            inside = sum(self._draft.has(a) for _, items in self._catalog.groups(category) for a in items)
            button = ui.button(on_click=lambda c=category: self._choose(c)) \
                .props(f"no-caps dense {'unelevated color=primary' if chosen else 'flat'}") \
                .classes("shrink-0 justify-start w-full")
            with button, ui.row().classes("no-wrap items-center w-full gap-2"):
                ui.label(title).classes("text-left flex-1 whitespace-nowrap")
                ui.label(f"{inside}/{count}").classes("text-xs opacity-60")

    @ui.refreshable_method
    def _available(self) -> None:
        if self._search:
            found = self._catalog.search(self._search)
            if not found:
                ui.label(f"No box matches {self._search!r}.").classes("opacity-70 p-2")
            for title, boxes in found:
                self._heading(title)
                for action in boxes:
                    self._box(action, add=True)
            return
        groups = self._catalog.groups(self._category)
        everything = [a for _, items in groups for a in items]
        if everything:
            self._heading(everything[0].category_title, self._category, everything, add=True)
        for group, boxes in groups:
            if group:
                self._heading(group, f"{self._category}/{group}", boxes, add=True, small=True)
            for action in boxes:
                self._box(action, add=True)

    @ui.refreshable_method
    def _count(self) -> None:
        inside = self._inside()
        total = sum(count for _, _, count in inside.categories())
        ui.label(f"In this filter: {total} box{'' if total == 1 else 'es'}").classes("font-semibold py-2")

    @ui.refreshable_method
    def _chosen(self) -> None:
        inside = self._inside()
        if not inside.categories():
            ui.label("Nothing yet. Click a box on the left, or the arrow on a heading for all of it.") \
                .classes("opacity-70 p-2")
        for category, title, _ in inside.categories():
            everything = [a for _, items in self._catalog.groups(category) for a in items]
            self._heading(title, category, everything, add=False)
            for group, boxes in inside.groups(category):
                if group:
                    part = f"{category}/{group}"
                    whole = [a for a in everything if (a.group or GENERAL) == group]
                    self._heading(group, part, whole, add=False, small=True)
                for action in boxes:
                    self._box(action, add=False)

    def _heading(self, text: str, part: str = "", boxes: list[RegisteredAction] | None = None, add: bool = True,
                 small: bool = False) -> None:
        """A category or sub group title; with `part` also the button that moves all of it."""
        with ui.row().classes("items-center no-wrap w-full gap-2 pt-2 px-2"):
            ui.label(text).classes("uppercase tracking-wide flex-1 "
                                   + ("text-xs font-bold opacity-60" if small else "text-sm font-bold"))
            if not part:
                return
            if not add and self._draft.whole(part):
                ui.label("whole: new boxes too").classes("text-xs opacity-60")
            done = add and all(self._draft.has(a) for a in boxes) and self._draft.whole(part)
            button = ui.button("All" if add else "None", icon="arrow_forward" if add else "arrow_back",
                               on_click=lambda: self._move_all(part, boxes, add)) \
                .props("flat dense no-caps size=sm" + (" disable" if done else ""))
            button.tooltip(f"Put all of {text} in the filter (boxes added later too)" if add
                           else f"Take all of {text} out of the filter")

    def _box(self, action: RegisteredAction, add: bool) -> None:
        inside = self._draft.has(action)
        row = ui.row().classes("items-center no-wrap w-full gap-2 rounded px-2 py-1 cursor-pointer "
                               "hover:bg-gray-500/15" + (" opacity-40" if add and inside else ""))
        with row.on("click", lambda: self._move(action, not inside if add else False)):
            if not add:
                ui.icon("arrow_back").classes("opacity-60")
            with ui.column().classes("gap-0 flex-1 min-w-0"):
                ui.label(action.title).classes("font-medium")
                ui.label(action.description or action.name).classes("text-xs opacity-70 truncate w-full")
            if add:
                ui.icon("check" if inside else "arrow_forward").classes("opacity-60")

    def _inside(self) -> ActionCatalog:
        return ActionCatalog(self._actions, box_filter=self._draft.to_filter())

    def _move(self, action: RegisteredAction, into: bool) -> None:
        (self._draft.add if into else self._draft.remove)(action)
        self._redraw()

    def _move_all(self, part: str, boxes: list[RegisteredAction], into: bool) -> None:
        (self._draft.add_all if into else self._draft.remove_all)(part, boxes)
        self._redraw()

    def _choose(self, category: str) -> None:
        self._category = category
        self._categories.refresh()
        self._available.refresh()

    def _searched(self, text: str) -> None:
        self._search = text
        self._categories.refresh()
        self._available.refresh()

    def _redraw(self) -> None:
        for part in (self._categories, self._available, self._count, self._chosen):
            part.refresh()

    def _save(self) -> None:
        try:
            self._filters.save(self._draft.to_filter(self._name.value or ""), self._old.name if self._old else "")
        except ValueError as e:
            ui.notify(str(e), type="warning")
            return
        self._dialog.submit(True)
