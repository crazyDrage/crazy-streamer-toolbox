import re
from collections.abc import Callable
from dataclasses import replace
from urllib.parse import quote

from nicegui import app, ui

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_outline import FlowOutline
from streamer_toolbox.core.flows.outline_entry import OutlineEntry
from streamer_toolbox.gui.components.folder_field import FolderField
from streamer_toolbox.gui.services.activity_log import ActivityLog


VIEWS = {"list": "List", "cards": "Cards"}
NO_FOLDER = "No folder"
NO_FOLDER_SHOW = "~"  # /flows?show=~ : the flows that are in no folder
OPEN_FOLDERS = "flows_page_open_folders"  # in the page settings: the names of the folders that are open
SEARCH_OPENS = 40  # a search opens the folders it found something in, up to this many flows
SELECTED = "flows_page_selected"  # in this browser tab's storage: the ticked flows' names while Select is on


class FlowsPage:
    """Every flow, sorted into folders (a flow's `folder`; the files and actions stay where they are): as a
    compact list (one row each) or as cards (with their boxes, folded), with a search. Per flow: Run, Edit, Move to
    folder, Duplicate, Save as template, Export, Delete; per folder: Rename, Dissolve, Export folder (all its flows
    as one file, to give to someone else). New flow (empty or from a template), Import (a flow or a folder file);
    the templates. Select puts a tick box on every flow: the ticked ones are moved to a folder or deleted
    together.

    A folder starts closed and its flows are only drawn when it is opened (hundreds of rows at once made the page
    slow); which folders are open is kept. The folders are also the page's side list (`side_items`):
    /flows?show=<folder> shows that folder alone, already open."""

    def __init__(self, library: FlowLibrary, actions: ActionRegistry, activity: ActivityLog) -> None:
        self._library = library
        self._actions = actions
        self._activity = activity

    def side_items(self) -> list[tuple[str, str, str] | tuple[str, str, str, bool]]:
        """The side list of the Flows area: a row per folder ("No folder" last, for the flows outside them) with
        its flows as sub rows (his wish of 2026-10-16: open the folders on the side and see the flows)."""
        flows = self._library.all()
        items: list[tuple[str, str, str] | tuple[str, str, str, bool]] = []
        for folder in [*self._library.folders(), ""]:
            inside = sorted((f for f in flows if f.folder == folder), key=lambda f: f.label.casefold())
            if not inside:
                continue
            show = quote(folder, safe="") if folder else NO_FOLDER_SHOW
            items.append((folder or NO_FOLDER, f"/flows?show={show}", "folder" if folder else "folder_off"))
            items += [(f.label, f"/flows/edit?flow={quote(f.name, safe='')}", "account_tree", True) for f in inside]
        return items

    def side_tool(self, redraw: Callable[[], None]) -> None:
        """At the bottom of the side list: New folder."""
        with ui.item().props("clickable dense").classes("opacity-80").on("click", lambda: self._new_folder(redraw)):
            with ui.item_section().props("avatar").classes("min-w-0 pr-3"):
                ui.icon("create_new_folder").classes("text-lg")
            with ui.item_section():
                ui.label("New folder")

    @staticmethod
    def _only() -> str | None:
        """The one folder this page shows ("" = the flows in none), None = all of them."""
        show = ui.context.client.request.query_params.get("show", "")
        return None if not show else "" if show == NO_FOLDER_SHOW else show

    @ui.refreshable_method
    def build(self) -> None:
        # the buttons, search and selection stay on top while the list scrolls (his wish, round 51)
        with ui.column().classes("tb-sticky w-full gap-2 py-2 -my-2"):
            with ui.row().classes("items-center gap-2"):
                ui.button("New flow", icon="add").props("no-caps unelevated href=/flows/edit")
                ui.button("Import", icon="upload", on_click=self._import).props("no-caps outline") \
                    .tooltip("A flow, or a folder of flows, that a toolbox exported")
                ui.button("New folder", icon="create_new_folder", on_click=lambda: self._new_folder()) \
                    .props("no-caps outline")
                ui.button("Select", icon="checklist",
                          on_click=lambda: self._select_mode(self._selected() is None)) \
                    .props("no-caps " + ("unelevated" if self._selected() is not None else "outline")) \
                    .tooltip("Tick several flows, then move or delete them together")
                templates = self._library.templates()
                if templates:
                    with ui.button("From template", icon="bookmarks").props("no-caps outline"):
                        with ui.menu():
                            for template in templates:
                                ui.menu_item(template.label, on_click=lambda t=template: ui.navigate.to(
                                    f"/flows/edit?template={t.name}"))
                ui.space()
                search = ui.input(placeholder="Search flows").props("dense outlined clearable").classes("w-56")
                with search.add_slot("prepend"):
                    ui.icon("search")
                ui.button(icon="unfold_less", on_click=lambda: self._close_all(search.value or "")) \
                    .props("flat round dense").tooltip("Close all folders")
                ui.toggle(VIEWS, value=app.storage.general.get("flows_page_view", "list"),
                          on_change=lambda e: self._set_view(e.value, search.value or "")).props("no-caps dense")
            search.on_value_change(lambda: self._flows.refresh(search.value or ""))
            self._selection_bar()
        self._flows()
        if templates:
            ui.label("Templates").classes("text-lg font-semibold pt-4")
            with ui.row().classes("gap-2"):
                for template in templates:
                    self._template_card(template)

    def _set_view(self, view: str, search: str) -> None:
        app.storage.general["flows_page_view"] = view
        self._flows.refresh(search)

    # ---- several flows at once ----

    @staticmethod
    def _selected() -> list[str] | None:
        """The ticked flows of this browser tab; None while Select is off."""
        return app.storage.client.get(SELECTED)

    def _select_mode(self, on: bool) -> None:
        app.storage.client[SELECTED] = [] if on else None
        self.build.refresh()

    def _tick(self, name: str, on: bool) -> None:
        names = [n for n in self._selected() or [] if n != name]
        app.storage.client[SELECTED] = names + [name] if on else names
        self._selection_bar.refresh()

    def _tick_box(self, flow: Flow) -> ui.checkbox | None:
        """The flow's tick box while Select is on."""
        selected = self._selected()
        if selected is None:
            return None
        return ui.checkbox(value=flow.name in selected,
                           on_change=lambda e, f=flow: self._tick(f.name, e.value)).props("dense")

    @ui.refreshable_method
    def _selection_bar(self) -> None:
        selected = self._selected()
        if selected is None:
            return
        flows = [f for f in self._library.all() if f.name in selected]
        with ui.row().classes("items-center gap-2 w-full px-3 py-1 rounded bg-primary/10"):
            ui.label(f"{len(flows)} selected" if flows else "Tick the flows (open a folder to see them)") \
                .classes("text-sm font-medium")
            ui.space()
            ui.button("Move to folder", icon="drive_file_move", on_click=lambda: self._move_many(flows)) \
                .props("no-caps flat dense" + ("" if flows else " disable"))
            ui.button("Delete", icon="delete", on_click=lambda: self._delete_many(flows)) \
                .props("no-caps flat dense color=negative" + ("" if flows else " disable"))
            ui.button("Done", on_click=lambda: self._select_mode(False)).props("no-caps flat dense")

    async def _move_many(self, flows: list[Flow]) -> None:
        folder = await self._ask_folder(f"Move {len(flows)} flow{'s' if len(flows) > 1 else ''} to", "")
        if folder is None:
            return
        for flow in flows:
            self._library.move(flow.name, folder)
        ui.notify(f"{len(flows)} moved to {folder or NO_FOLDER}", type="positive")
        self._select_mode(True)

    async def _delete_many(self, flows: list[Flow]) -> None:
        names = ", ".join(f.label for f in flows)
        if await _sure(f"Delete {len(flows)} flow{'s' if len(flows) > 1 else ''}?",
                       f"{names}. Their files and actions are deleted. SAMMI buttons and flows that call them "
                       "will fail."):
            for flow in flows:
                self._library.delete(flow.name)
            ui.notify(f"{len(flows)} deleted")
            self._select_mode(True)

    def _close_all(self, search: str) -> None:
        app.storage.general[OPEN_FOLDERS] = []
        self._flows.refresh(search)

    @ui.refreshable_method
    def _flows(self, search: str = "") -> None:
        flows = self._library.all()
        if not flows:
            ui.label("No flows yet. Press New flow.").classes("opacity-70")
            return
        only = self._only()
        if only is not None:
            flows = [f for f in flows if f.folder == only]
            if not flows:
                ui.label(f"No flows in {only or NO_FOLDER}.").classes("opacity-70")
                return
        words = search.casefold().split()
        if words:
            flows = [f for f in flows if all(w in f"{f.label} {f.name} {f.folder} {f.description}".casefold()
                                             for w in words)]
            if not flows:
                ui.label(f"No flow matches {search!r}.").classes("opacity-70")
                return
        cards = app.storage.general.get("flows_page_view", "list") == "cards"
        # a search shows what it found, unless that is most of the list; it doesn't change what is kept as open
        found = bool(words) and len(flows) <= SEARCH_OPENS
        remembered = app.storage.general.get(OPEN_FOLDERS, [])
        folders = sorted({f.folder for f in flows if f.folder}, key=str.casefold) + [""]
        for folder in folders:
            inside = [f for f in flows if f.folder == folder]
            if inside:
                self._folder(folder, inside, cards, only is not None or found or folder in remembered,
                             keep=only is None and not found)

    def _folder(self, folder: str, flows: list[Flow], cards: bool, opened: bool, keep: bool) -> None:
        with ui.expansion(value=opened).props("dense switch-toggle-side").classes("w-full") as section:
            with section.add_slot("header"):
                with ui.row().classes("items-center no-wrap w-full gap-2"):
                    ui.icon("folder" if folder else "folder_off").classes("text-primary text-xl")
                    ui.label(folder or NO_FOLDER).classes("font-semibold")
                    ui.label(str(len(flows))).classes("text-xs opacity-60")
            content = ui.column().classes("w-full gap-0")
        drawn = False

        def draw() -> None:
            nonlocal drawn
            if not drawn:
                drawn = True
                with content:
                    self._folder_content(folder, flows, cards)

        def toggled(value: bool) -> None:
            if value:
                draw()
            if keep:
                self._remember(folder, value)

        if opened:
            draw()
        section.on_value_change(lambda e: toggled(e.value))

    def _folder_content(self, folder: str, flows: list[Flow], cards: bool) -> None:
        if folder:
            with ui.row().classes("gap-1 pl-2"):
                ui.button("Rename folder", icon="edit", on_click=lambda: self._rename_folder(folder)) \
                    .props("flat dense no-caps size=sm")
                ui.button("Dissolve", icon="folder_off", on_click=lambda: self._dissolve(folder)) \
                    .props("flat dense no-caps size=sm").tooltip(f"Its flows go to {NO_FOLDER}")
                ui.button("Export folder", icon="download", on_click=lambda: self._export_folder(folder)) \
                    .props("flat dense no-caps size=sm") \
                    .tooltip("All its flows as one file, to give to someone else: they bring it in with Import")
        boxes: list[ui.checkbox] = []
        if self._selected() is not None:
            with ui.row().classes("gap-1 pl-2"):
                ui.button("Tick all here", icon="done_all", on_click=lambda: [b.set_value(True) for b in boxes]) \
                    .props("flat dense no-caps size=sm")
                ui.button("None here", icon="remove_done", on_click=lambda: [b.set_value(False) for b in boxes]) \
                    .props("flat dense no-caps size=sm")
        if cards:
            with ui.element("div").classes("grid gap-4 w-full lg:grid-cols-2 items-start pt-1"):
                for flow in flows:
                    boxes.append(self._card(flow))
        else:
            with ui.column().classes("w-full gap-0"):
                for flow in flows:
                    boxes.append(self._row(flow))

    @staticmethod
    def _remember(folder: str, opened: bool) -> None:
        names = [n for n in app.storage.general.get(OPEN_FOLDERS, []) if n != folder]
        app.storage.general[OPEN_FOLDERS] = names + [folder] if opened else names

    def _row(self, flow: Flow) -> ui.checkbox | None:
        """One flow in the list: name (opens it), a short line under it, ⚡ for triggers, Run / Edit / more.
        Gives its tick box while Select is on."""
        with ui.row().classes("items-center no-wrap w-full gap-2 px-2 py-1 rounded hover:bg-primary/10"):
            box = self._tick_box(flow)
            ui.icon("account_tree").classes("text-primary" if flow.enabled else "opacity-40")
            with ui.column().classes("gap-0 min-w-0 flex-1" + ("" if flow.enabled else " opacity-50")):
                ui.link(flow.label, f"/flows/edit?flow={flow.name}").classes("font-medium no-underline truncate")
                inputs = ", ".join(i.name for i in flow.inputs)
                line = flow.description or f"{len(flow.nodes)} boxes" + (f" · inputs: {inputs}" if inputs else "")
                ui.label(("Switched off · " if not flow.enabled else "") + line) \
                    .classes("text-xs opacity-60 truncate w-full")
            self._switches(flow)
            button = ui.button(icon="play_arrow").props("flat round dense").tooltip("Run")
            button.on_click(lambda f=flow, b=button: self._run(f, b))
            ui.button(icon="edit").props(f"flat round dense href=/flows/edit?flow={flow.name}").tooltip("Edit")
            self._more(flow)
            self._right_click(flow, button)
        return box

    def _switches(self, flow: Flow) -> None:
        """The flow's two switches in the list: ⚡ its triggers (only when it has some), ⏻ the flow itself.
        Lit = on. A click flips it and saves the flow."""
        if flow.triggers:
            listening = flow.enabled and flow.triggers_enabled
            what = "; ".join(f"{t.kind} " + ", ".join(f"{k} = {v}" for k, v in t.match.items())
                             for t in flow.triggers)
            ui.button(icon="bolt" if flow.triggers_enabled else "flash_off",
                      on_click=lambda f=flow: self._switch(f, triggers_enabled=not f.triggers_enabled)) \
                .props("flat round dense " + ("color=warning" if listening else "color=grey")) \
                .tooltip((f"Triggers on: also starts by itself ({what}). Click to switch its triggers off"
                          if flow.triggers_enabled else
                          f"Triggers off: {what} don't start it. Click to switch them on")
                         + ("" if flow.enabled else ". The flow itself is switched off"))
        ui.button(icon="power_settings_new", on_click=lambda f=flow: self._switch(f, enabled=not f.enabled)) \
            .props("flat round dense " + ("color=positive" if flow.enabled else "color=grey")) \
            .tooltip("Flow on. Click to switch it off: then nothing starts it" if flow.enabled else
                     "Flow off: nothing starts it (button, SAMMI, API, other flows, triggers). Click to "
                     "switch it on")

    def _switch(self, flow: Flow, **switches: bool) -> None:
        self._library.save(replace(flow, **switches))
        self.build.refresh()

    def _more(self, flow: Flow) -> None:
        with ui.button(icon="more_vert").props("flat round dense"):
            with ui.menu():
                ui.menu_item("Move to folder", on_click=lambda f=flow: self._move(f))
                ui.menu_item("Duplicate", on_click=lambda f=flow: self._duplicate(f))
                ui.menu_item("Save as template", on_click=lambda f=flow: self._template(f))
                ui.menu_item("Export (download file)", on_click=lambda f=flow: self._export(f))
                ui.menu_item("Delete", on_click=lambda f=flow: self._delete(f))

    def _right_click(self, flow: Flow, run: ui.button) -> None:
        """The right click menu on a flow's row or card (his "go" of 2026-10-14); run: its Run button, which
        shows that it runs."""
        with ui.context_menu():
            ui.menu_item("Open", on_click=lambda f=flow: ui.navigate.to(f"/flows/edit?flow={f.name}")).props("dense")
            ui.menu_item("Open in new window", on_click=lambda f=flow: ui.run_javascript(
                f"tbNewWindow('/flows/edit?flow={quote(f.name)}')")).props("dense")
            ui.menu_item("Run", on_click=lambda f=flow, b=run: self._run(f, b)).props("dense")
            ui.menu_item("Move to folder", on_click=lambda f=flow: self._move(f)).props("dense")
            ui.menu_item("Export (download file)", on_click=lambda f=flow: self._export(f)).props("dense")
            ui.menu_item("Delete", on_click=lambda f=flow: self._delete(f)).props("dense").classes("text-negative")

    async def _move(self, flow: Flow) -> None:
        folder = await self._ask_folder(f"Move {flow.label} to", flow.folder)
        if folder is not None and folder != flow.folder:
            self._library.move(flow.name, folder)
            self.build.refresh()

    async def _ask_folder(self, title: str, current: str) -> str | None:
        """Pick a folder from the list or type one (a new name makes a new folder); None when cancelled."""
        field = FolderField(self._library.folders(), current, "Folder (pick or type a new one)")
        with ui.dialog() as dialog, ui.card().classes("w-96 max-w-full gap-3"):
            ui.label(title).classes("font-semibold")
            field.build().classes("w-full")
            ui.label("Empty = No folder. Only the Flows page sorts by it: SAMMI, buttons and triggers keep "
                     "working.").classes("text-xs opacity-60")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat no-caps")
                ui.button("Move", on_click=lambda: dialog.submit(field.value)).props("unelevated no-caps")
        folder = await dialog
        dialog.delete()
        return folder

    async def _new_folder(self, redraw_side: Callable[[], None] | None = None) -> None:
        """A name and the flows to put in it (a folder only exists while a flow is in it). redraw_side: the side
        list it was asked from, drawn again with the new folder in it."""
        flows = self._library.all()
        with ui.dialog() as dialog, ui.card().classes("w-[28rem] max-w-full gap-3"):
            ui.label("New folder").classes("text-lg font-semibold")
            name = ui.input("Name").props("outlined dense autofocus").classes("w-full")
            ui.label("Tick the flows that go in it").classes("text-sm")
            with ui.column().classes("gap-0 w-full max-h-[50vh] overflow-auto"):
                ticks = {f.name: ui.checkbox(f.label + (f"  ({f.folder})" if f.folder else "")).props("dense")
                         for f in flows}
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat no-caps")
                ui.button("Create", icon="create_new_folder", on_click=lambda: dialog.submit(
                    (name.value or "", [n for n, box in ticks.items() if box.value]))).props("unelevated no-caps")
        result = await dialog
        dialog.delete()
        if not result:
            return
        folder, chosen = result[0].strip(), result[1]
        if not folder or not chosen:
            ui.notify("A folder needs a name and at least one flow in it", type="warning")
            return
        for flow_name in chosen:
            self._library.move(flow_name, folder)
        ui.notify(f"Folder {folder}: {len(chosen)} flow{'s' if len(chosen) > 1 else ''}", type="positive")
        self.build.refresh()
        if redraw_side:
            redraw_side()

    async def _rename_folder(self, folder: str) -> None:
        with ui.dialog() as dialog, ui.card().classes("w-80 max-w-full gap-3"):
            ui.label(f"Rename folder {folder}").classes("font-semibold")
            name = ui.input("New name", value=folder).props("outlined dense autofocus").classes("w-full")
            name.on("keydown.enter", lambda: dialog.submit(name.value))
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat no-caps")
                ui.button("Rename", on_click=lambda: dialog.submit(name.value)).props("unelevated no-caps")
        new = await dialog
        dialog.delete()
        if new and new.strip() and new.strip() != folder:
            self._library.rename_folder(folder, new.strip())
            app.storage.general[OPEN_FOLDERS] = [new.strip() if n == folder else n  # an open one stays open
                                                 for n in app.storage.general.get(OPEN_FOLDERS, [])]
            self.build.refresh()

    def _dissolve(self, folder: str) -> None:
        self._library.rename_folder(folder, "")
        self._remember(folder, False)
        ui.notify(f"Folder {folder} dissolved: its flows are under {NO_FOLDER}")
        self.build.refresh()

    def _template_card(self, template: Flow) -> None:
        count = len(template.nodes)
        with ui.card().classes("gap-1 p-3"):
            with ui.row().classes("items-center no-wrap gap-2"):
                ui.icon("bookmark").classes("text-primary")
                ui.label(template.label).classes("font-medium")
                ui.label(f"{count} box" + ("" if count == 1 else "es")).classes("text-xs opacity-60")
            with ui.row().classes("gap-1"):
                ui.button("Use", on_click=lambda: ui.navigate.to(f"/flows/edit?template={template.name}")) \
                    .props("no-caps flat dense")
                ui.button("Delete", on_click=lambda: self._delete_template(template)) \
                    .props("no-caps flat dense color=negative")

    def _card(self, flow: Flow) -> ui.checkbox | None:
        with ui.card().classes("w-full gap-2"):
            with ui.row().classes("items-center w-full gap-2"):
                box = self._tick_box(flow)
                ui.icon("account_tree").classes("text-xl text-primary")
                ui.label(flow.label).classes("text-lg font-semibold")
                if flow.triggers:
                    ui.badge(" · ".join(t.kind for t in flow.triggers)).props("color=warning text-color=black") \
                        .classes("text-xs").tooltip("Also starts by itself: " + "; ".join(
                            f"{t.kind} " + ", ".join(f"{k} = {v}" for k, v in t.match.items()) for t in flow.triggers))
                ui.space()
                self._switches(flow)
                button = ui.button("Run", icon="play_arrow").props("no-caps unelevated")
                button.on_click(lambda f=flow, b=button: self._run(f, b))
                ui.button("Edit", icon="edit").props(f"no-caps outline href=/flows/edit?flow={flow.name}")
                self._more(flow)
                self._right_click(flow, button)
            if flow.description:
                ui.label(flow.description).classes("text-sm opacity-80")
            inputs = ", ".join(i.name + ("" if i.default is None else f" = {i.default}") for i in flow.inputs)
            ui.label(f"Action {flow.action_name}" + (f" · inputs: {inputs}" if inputs else "") +
                     " · SAMMI, Kit and the Live page can run it").classes("text-xs opacity-60")
            count = len(flow.nodes)
            # folded: a long flow would fill the page; the ⚡ badge above already says it has triggers
            with ui.expansion(f"Show boxes ({count})" + (" and triggers" if flow.triggers else ""), icon="list") \
                .props("dense").classes("w-full text-sm"):
                self._outline(flow, FlowOutline(flow, self._ports, self._lines).build())
                for trigger in flow.triggers:
                    with ui.row().classes("items-center gap-1 text-sm pt-1"):
                        ui.icon("bolt").classes("text-warning")
                        ui.label(f"Also starts on {trigger.kind}: " +
                                 ", ".join(f"{k} = {v}" for k, v in trigger.match.items()))
        return box

    def _outline(self, flow: Flow, entries: tuple[OutlineEntry, ...]) -> None:
        for entry in entries:
            if entry.kind == "node":
                self._node_line(flow, entry)
            elif entry.kind == "ref":
                ui.label(f"↪ goes on at box {entry.node_id}").classes("text-xs opacity-60 pl-6")
            else:
                ui.label("at the same time:").classes("text-xs font-semibold text-primary pl-2")
            for port, branch in entry.branches:
                with ui.column().classes("gap-1 pl-4 ml-2 border-l-2 border-primary/40"):
                    if port:
                        ui.label(port).classes("text-xs font-semibold text-primary")
                    self._outline(flow, branch)

    def _node_line(self, flow: Flow, entry: OutlineEntry) -> None:
        node = flow.node(entry.node_id)
        action = self._actions.get(node.action) if node.action in self._actions else None
        with ui.row().classes("items-start no-wrap gap-2 text-sm" + ("" if node.enabled else " opacity-40")):
            ui.icon("call_split" if entry.branches else "check_box_outline_blank").classes("text-primary pt-0.5")
            with ui.column().classes("gap-0 min-w-0"):
                ui.label((action.title if action else node.action) + ("" if node.enabled else "  (off)")) \
                    .classes("font-medium")
                details = ", ".join(f"{k} = {v}" for k, v in node.params.items())
                if node.save_as:
                    details += f"  → {node.save_as}"
                if details:
                    ui.label(details.strip()).classes("text-xs opacity-70 break-all")

    def _ports(self, action: str, params: dict) -> tuple[str, ...]:
        found = self._actions.get(action) if action in self._actions else None
        return (found.ports_for(params) if found else ()) or ("done",)

    def _lines(self, action: str, params: dict) -> list[str]:
        return self._actions.get(action).entry_lines(params) if action in self._actions else []

    async def _run(self, flow: Flow, button: ui.button) -> None:
        if any(i.default is None for i in flow.inputs):
            ui.notify("This flow needs inputs: run it from the Live page, it asks for them", type="warning")
            return
        button.props("loading")
        try:
            result = await self._actions.run(flow.action_name)
        except Exception as e:
            self._activity.add("GUI", flow.action_name, False, e)
            ui.notify(str(e), type="negative", multi_line=True)
        else:
            self._activity.add("GUI", flow.action_name, True, f"{len(result)} boxes")
            ui.notify(f"{flow.label} done", type="positive")
        finally:
            button.props(remove="loading")

    def _duplicate(self, flow: Flow) -> None:
        label = f"{flow.label} copy"
        self._library.save(replace(flow, name=self._library.free_name(label), label=label, triggers=()))
        ui.notify(f"{label} created" + (" (without its triggers, so a redeem doesn't start both)"
                                        if flow.triggers else ""), type="positive")
        self.build.refresh()

    def _export(self, flow: Flow) -> None:
        ui.download.content(self._library.export_text(flow.name), f"{flow.name}.toml", "application/toml")

    def _export_folder(self, folder: str) -> None:
        pack = self._library.folder_pack(folder)
        ui.download.content(pack.to_text(), f"{_file_name(folder)}.flows.toml", "application/toml")
        along = [f.label for f in pack.flows if f.folder != folder]
        if along:
            ui.notify(f"Also in the file, because the folder's flows use them as boxes: {', '.join(along)}.",
                      type="info", multi_line=True, timeout=10000, close_button="OK")

    async def _import(self) -> None:
        with ui.dialog() as dialog, ui.card().classes("w-[28rem] max-w-full gap-3"):
            ui.label("Import").classes("text-lg font-semibold")
            ui.label("Pick a file a toolbox exported: one flow (.toml) or a folder of flows (.flows.toml).") \
                .classes("text-sm opacity-80")
            ui.label("Flows from someone else can do everything your own can: look at them before you switch "
                     "on what you don't know.").classes("text-xs opacity-60")

            async def uploaded(e) -> None:
                try:
                    text = (await e.file.read()).decode("utf-8")
                    flows = self._library.import_file(text, e.file.name)
                except Exception as error:
                    ui.notify(f"Not imported: {error}", type="negative", multi_line=True)
                    return
                dialog.submit(flows)

            ui.upload(on_upload=uploaded, auto_upload=True, max_files=1) \
                .props('accept=".toml" flat bordered label="Press + to pick the file, or drop it here"') \
                .classes("w-full")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("no-caps flat")
        flows = await dialog
        dialog.delete()
        if not flows:
            return
        copies = [f.label for f in flows if f.label.endswith("(imported)")]
        note = (f" {len(copies)} came in without triggers, because a flow with that name was there already: "
                f"{', '.join(copies)}." if copies else "")
        what = flows[0].label if len(flows) == 1 else f"{len(flows)} flows"
        where = f" (folder {flows[0].folder})" if len(flows) > 1 and flows[0].folder else ""
        ui.notify(f"{what} imported{where}.{note}", type="positive", multi_line=True)
        self.build.refresh()

    def _template(self, flow: Flow) -> None:
        self._library.save_template(replace(flow, name=self._library.free_template_name(flow.label)))
        ui.notify(f"Template {flow.label} saved", type="positive")
        self.build.refresh()

    async def _delete(self, flow: Flow) -> None:
        if await _sure(f"Delete the flow {flow.label}?",
                       f"Deletes {self._library.folder / (flow.name + '.toml')} and the action "
                       f"{flow.action_name}. SAMMI buttons that call it will fail."):
            self._library.delete(flow.name)
            ui.notify(f"{flow.label} deleted")
            self.build.refresh()

    async def _delete_template(self, template: Flow) -> None:
        if await _sure(f"Delete the template {template.label}?", "Flows made from it stay."):
            self._library.delete_template(template.name)
            self.build.refresh()


def _file_name(folder: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", folder.casefold()).strip("_") or "flows"


async def _sure(question: str, detail: str) -> bool:
    """A yes/no on this screen only (the ConfirmService asks on every open screen)."""
    with ui.dialog() as dialog, ui.card().classes("w-[28rem] max-w-full gap-4"):
        ui.label(question).classes("text-lg font-semibold")
        ui.label(detail).classes("text-sm opacity-80")
        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancel", on_click=lambda: dialog.submit(False)).props("no-caps flat")
            ui.button("Delete", icon="delete", on_click=lambda: dialog.submit(True)) \
                .props("no-caps unelevated color=negative")
    result = await dialog
    dialog.delete()
    return bool(result)
