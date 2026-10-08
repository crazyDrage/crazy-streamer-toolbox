from nicegui import app, ui

from collections.abc import Callable

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.box_filter_store import BoxFilterStore
from streamer_toolbox.core.actions.registered_action import RegisteredAction
from streamer_toolbox.gui.components.flow_editor.action_catalog import ActionCatalog
from streamer_toolbox.gui.components.flow_editor.fold_group import FoldGroup

SwitchedOff = Callable[[], dict[str, str]]  # box category → name, for the connections and plugins that are off


class ActionPicker:
    """The Add box window: a search on top, the categories on the left (on a phone: a row on top) with how many
    boxes each has, and on the right the chosen category's boxes by sub group, each with its one line of help.
    Searching lists the matching boxes of every category; Enter takes the first one. Show narrows all of it to
    one filter (the basic ones, and his own from Settings); the one picked stays for the next time. The boxes
    of programs that are switched off under Connections, and of plugins switched off under Plugins, are left
    out, with one line to show them anyway."""

    def __init__(self, actions: ActionRegistry, exclude: str = "", filters: BoxFilterStore | None = None,
                 switched_off: SwitchedOff | None = None) -> None:
        self._actions = actions
        self._exclude = exclude  # the flow being edited, so it can't call itself
        self._filters = filters
        has_boxes = {a.category for a in actions.all(include_flow_only=True)}
        # category → the program's name (a connection without boxes, like Keyboard, isn't named)
        self._off = {c: name for c, name in (switched_off() if switched_off else {}).items() if c in has_boxes}
        self._show_off = False
        self._search = ""
        self._use_filter(app.storage.general.get(FILTER_KEY, "") if filters else "")

    def _use_filter(self, name: str) -> None:
        box_filter = self._filters.get(name) if self._filters and name else None  # a deleted one: all boxes
        self._filter = box_filter.name if box_filter else ""
        self._catalog = ActionCatalog(self._actions, self._exclude, box_filter,
                                      () if self._show_off else tuple(self._off))
        self._category = next(iter(self._catalog.categories()), ("", "", 0))[0]

    async def pick(self, title: str = "Add a box") -> str | None:
        """Opens the window; the chosen action's name, or None."""
        with ui.dialog() as dialog, ui.card().classes("w-[60rem] max-w-full h-[85vh] gap-2 p-3"):
            self._dialog = dialog
            with ui.row().classes("items-center w-full no-wrap gap-2"):
                ui.label(title).classes("text-lg font-semibold")
                search = self._search_input = ui.input(placeholder="Search, e.g. scene, volume, hotkey, rats") \
                    .props("autofocus clearable dense outlined debounce=150").classes("flex-1")
                if self._filters:
                    shown = {"": ALL_BOXES} | {f.name: f.name for f in self._filters.all()}
                    ui.select(shown, value=self._filter, label="Show", on_change=lambda e: self._show(e.value)) \
                        .props("dense outlined options-dense").classes("w-44 shrink-0") \
                        .tooltip("Only the boxes of one filter. Make your own in Settings → Box filters")
                ui.button(icon="close", on_click=lambda: dialog.submit(None)).props("flat round dense")
            with ui.element("div").classes("flex flex-col sm:flex-row w-full flex-1 min-h-0 gap-3"):
                with ui.element("div").classes("flex flex-wrap sm:flex-col sm:flex-nowrap gap-1 overflow-auto shrink-0 "
                                               "sm:w-48 sm:max-h-full pb-1 sm:pb-0 sm:pr-2 sm:border-r "
                                               "border-gray-500/30"):
                    self._categories()
                # max-h-full: the list scrolls inside the window (a q-scrollarea stayed short here)
                with ui.element("div").classes("flex-1 min-h-0 min-w-0 max-h-full overflow-y-auto"):
                    self._boxes()

            def searched(e) -> None:
                self._search = e.value or ""
                self._categories.refresh()
                self._boxes.refresh()

            search.on_value_change(searched)
            search.on("keydown.enter", self._take_first)
        result = await dialog
        dialog.delete()
        return result

    @ui.refreshable_method
    def _categories(self) -> None:
        counts = {title: len(items) for title, items in self._catalog.search(self._search)} if self._search \
            else None
        for category, category_title, count in self._catalog.categories():
            shown = count if counts is None else counts.get(category_title, 0)
            chosen = counts is None and category == self._category
            button = ui.button(on_click=lambda c=category: self._choose(c)) \
                .props(f"no-caps dense {'unelevated color=primary' if chosen else 'flat'}") \
                .classes("shrink-0 justify-start sm:w-full" + (" opacity-40" if counts is not None and not shown
                                                               else ""))
            with button, ui.row().classes("no-wrap items-center w-full gap-2"):
                ui.label(category_title).classes("text-left flex-1 whitespace-nowrap")
                ui.label(str(shown)).classes("text-xs opacity-60")
        if self._off:
            names = ", ".join(self._off.values())
            with ui.column().classes("gap-0 pt-2 px-1 shrink-0"):
                ui.label(f"Switched off: {names}").classes("text-xs opacity-60")
                ui.button("Hide them" if self._show_off else "Show them anyway", on_click=self._toggle_off) \
                    .props("flat dense no-caps size=sm").classes("self-start")

    @ui.refreshable_method
    def _boxes(self) -> None:
        if self._search:
            found = self._catalog.search(self._search)
            if not found:
                where = f" in {self._filter!r}. Show: {ALL_BOXES} looks everywhere" if self._filter else "."
                ui.label(f"No box matches {self._search!r}{where}").classes("opacity-70 p-2")
            for category_title, actions in found:
                with FoldGroup(category_title, len(actions)).body:
                    for action in actions:
                        self._box(action, group=True)
            return
        for group, actions in self._catalog.groups(self._category):
            # a category without sub groups is one plain list; a sub group has a heading that folds it
            with FoldGroup(group, len(actions)).body if group else ui.column().classes("w-full gap-0"):
                for action in actions:
                    self._box(action)

    def _box(self, action: RegisteredAction, group: bool = False) -> None:
        with ui.element("div").classes("w-full rounded px-2 py-1 cursor-pointer hover:bg-gray-500/15") \
                .on("click", lambda name=action.name: self._dialog.submit(name)):
            with ui.row().classes("no-wrap items-baseline gap-2"):
                ui.label(action.title).classes("font-medium")
                if group and action.group:
                    ui.label(action.group).classes("text-xs opacity-50")
            ui.label(action.description or action.name).classes("text-xs opacity-70")

    def _toggle_off(self) -> None:
        self._show_off = not self._show_off
        self._use_filter(self._filter)
        self._categories.refresh()
        self._boxes.refresh()

    def _show(self, name: str) -> None:
        app.storage.general[FILTER_KEY] = name or ""
        self._use_filter(name or "")
        self._categories.refresh()
        self._boxes.refresh()

    def _choose(self, category: str) -> None:
        self._category = category
        if self._search:  # a category click while searching: show that category (emptying the search refreshes)
            self._search_input.set_value("")
            return
        self._categories.refresh()
        self._boxes.refresh()

    def _take_first(self) -> None:
        found = self._catalog.search(self._search)
        if found:
            self._dialog.submit(found[0][1][0].name)


ALL_BOXES = "All boxes"
FILTER_KEY = "box_filter"  # app.storage.general: the filter last picked in the Add box window
