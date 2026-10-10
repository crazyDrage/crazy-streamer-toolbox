from collections.abc import Mapping

from nicegui import ui

from streamer_toolbox.gui.components.flow_editor.fold_group import FoldGroup
from streamer_toolbox.gui.components.flow_editor.trigger_catalog import TriggerCatalog
from streamer_toolbox.gui.components.flow_editor.trigger_entry import TriggerEntry


class TriggerPicker:
    """The Add trigger window, built like the Add box window: a search on top, the groups on the left (on a
    phone: a row on top) with how many triggers each has, and on the right the chosen group's triggers, each
    with one line of what it is and what it gives the flow. Searching lists the matching triggers of every
    group; Enter takes the first one. `note` is one small line below the groups (how many triggers are
    hidden, and why)."""

    def __init__(self, kinds: Mapping[str, tuple[str, str, str, str]], note: str = "") -> None:
        self._note = note
        self._catalog = TriggerCatalog(kinds)
        self._group = next(iter(self._catalog.groups()), ("", 0))[0]
        self._search = ""

    async def pick(self, title: str = "Add a trigger") -> TriggerEntry | None:
        """Opens the window; the chosen trigger, or None."""
        with ui.dialog() as dialog, ui.card().classes("w-[52rem] max-w-full h-[80vh] gap-2 p-3"):
            self._dialog = dialog
            with ui.row().classes("items-center w-full no-wrap gap-2"):
                ui.label(title).classes("text-lg font-semibold")
                search = self._search_input = ui.input(placeholder="Search, e.g. chat, sub, redeem, hotkey") \
                    .props("autofocus clearable dense outlined debounce=150").classes("flex-1")
                ui.button(icon="close", on_click=lambda: dialog.submit(None)).props("flat round dense")
            with ui.element("div").classes("flex flex-col sm:flex-row w-full flex-1 min-h-0 gap-3"):
                with ui.element("div").classes("flex flex-wrap sm:flex-col sm:flex-nowrap gap-1 overflow-auto shrink-0 "
                                               "sm:w-48 sm:max-h-full pb-1 sm:pb-0 sm:pr-2 sm:border-r "
                                               "border-gray-500/30"):
                    self._groups()
                with ui.element("div").classes("flex-1 min-h-0 min-w-0 max-h-full overflow-y-auto"):
                    self._triggers()

            def searched(e) -> None:
                self._search = e.value or ""
                self._groups.refresh()
                self._triggers.refresh()

            search.on_value_change(searched)
            search.on("keydown.enter", self._take_first)
        result = await dialog
        dialog.delete()
        return result

    @ui.refreshable_method
    def _groups(self) -> None:
        counts = {group: len(items) for group, items in self._catalog.search(self._search)} if self._search \
            else None
        for group, count in self._catalog.groups():
            shown = count if counts is None else counts.get(group, 0)
            chosen = counts is None and group == self._group
            button = ui.button(on_click=lambda g=group: self._choose(g)) \
                .props(f"no-caps dense {'unelevated color=primary' if chosen else 'flat'}") \
                .classes("shrink-0 justify-start sm:w-full" + (" opacity-40" if counts is not None and not shown
                                                               else ""))
            with button, ui.row().classes("no-wrap items-center w-full gap-2"):
                ui.label(group).classes("text-left flex-1 whitespace-nowrap")
                ui.label(str(shown)).classes("text-xs opacity-60")
        if self._note:
            ui.label(self._note).classes("text-xs opacity-60 pt-2 px-1")

    @ui.refreshable_method
    def _triggers(self) -> None:
        if not self._search:
            for entry in self._catalog.entries(self._group):
                self._trigger(entry)
            return
        found = self._catalog.search(self._search)
        if not found:
            ui.label(f"No trigger matches {self._search!r}.").classes("opacity-70 p-2")
        for group, entries in found:
            with FoldGroup(group, len(entries)).body:
                for entry in entries:
                    self._trigger(entry)

    def _trigger(self, entry: TriggerEntry) -> None:
        with ui.row().classes("w-full no-wrap items-start gap-3 rounded px-2 py-1 cursor-pointer "
                              "hover:bg-gray-500/15").on("click", lambda e=entry: self._dialog.submit(e)):
            ui.icon(entry.icon).classes("text-primary text-xl pt-1")
            with ui.column().classes("gap-0 min-w-0"):
                ui.label(entry.title).classes("font-medium")
                if entry.info:
                    ui.label(entry.info).classes("text-xs opacity-70")
                if entry.fields:
                    ui.label("Gives: " + ", ".join(entry.fields)).classes("text-xs opacity-50")

    def _choose(self, group: str) -> None:
        self._group = group
        if self._search:  # a group click while searching: show that group (emptying the search refreshes)
            self._search_input.set_value("")
            return
        self._groups.refresh()
        self._triggers.refresh()

    def _take_first(self) -> None:
        found = self._catalog.search(self._search)
        if found:
            self._dialog.submit(found[0][1][0])
