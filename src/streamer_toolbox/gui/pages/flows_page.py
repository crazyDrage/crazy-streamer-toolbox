from dataclasses import replace

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


class FlowsPage:
    """Every flow, sorted into folders (a flow's `folder`; the files and actions stay where they are): as a
    compact list (one row each) or as cards (with their boxes, folded), with a search. Per flow: Run, Edit, Move to
    folder, Duplicate, Save as template, Export, Delete; per folder: Rename, Dissolve. New flow (empty or from a
    template), Import flow; the templates."""

    def __init__(self, library: FlowLibrary, actions: ActionRegistry, activity: ActivityLog) -> None:
        self._library = library
        self._actions = actions
        self._activity = activity

    @ui.refreshable_method
    def build(self) -> None:
        with ui.row().classes("items-center gap-2"):
            ui.button("New flow", icon="add").props("no-caps unelevated href=/flows/edit")
            ui.button("Import flow", icon="upload", on_click=self._import).props("no-caps outline")
            ui.button("New folder", icon="create_new_folder", on_click=self._new_folder).props("no-caps outline")
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
            ui.toggle(VIEWS, value=app.storage.general.get("flows_page_view", "list"),
                      on_change=lambda e: self._set_view(e.value, search.value or "")).props("no-caps dense")
        search.on_value_change(lambda: self._flows.refresh(search.value or ""))
        self._flows()
        if templates:
            ui.label("Templates").classes("text-lg font-semibold pt-4")
            with ui.row().classes("gap-2"):
                for template in templates:
                    self._template_card(template)

    def _set_view(self, view: str, search: str) -> None:
        app.storage.general["flows_page_view"] = view
        self._flows.refresh(search)

    @ui.refreshable_method
    def _flows(self, search: str = "") -> None:
        flows = self._library.all()
        if not flows:
            ui.label("No flows yet. Press New flow.").classes("opacity-70")
            return
        words = search.casefold().split()
        if words:
            flows = [f for f in flows if all(w in f"{f.label} {f.name} {f.folder} {f.description}".casefold()
                                             for w in words)]
            if not flows:
                ui.label(f"No flow matches {search!r}.").classes("opacity-70")
                return
        cards = app.storage.general.get("flows_page_view", "list") == "cards"
        folders = sorted({f.folder for f in flows if f.folder}, key=str.casefold) + [""]
        for folder in folders:
            inside = [f for f in flows if f.folder == folder]
            if inside:
                self._folder(folder, inside, cards)

    def _folder(self, folder: str, flows: list[Flow], cards: bool) -> None:
        with ui.expansion(value=True).props("dense switch-toggle-side").classes("w-full") as section:
            with section.add_slot("header"):
                with ui.row().classes("items-center no-wrap w-full gap-2"):
                    ui.icon("folder" if folder else "folder_off").classes("text-primary text-xl")
                    ui.label(folder or NO_FOLDER).classes("font-semibold")
                    ui.label(str(len(flows))).classes("text-xs opacity-60")
            if folder:
                with ui.row().classes("gap-1 pl-2"):
                    ui.button("Rename folder", icon="edit", on_click=lambda: self._rename_folder(folder)) \
                        .props("flat dense no-caps size=sm")
                    ui.button("Dissolve", icon="folder_off", on_click=lambda: self._dissolve(folder)) \
                        .props("flat dense no-caps size=sm").tooltip(f"Its flows go to {NO_FOLDER}")
            if cards:
                with ui.element("div").classes("grid gap-4 w-full lg:grid-cols-2 items-start pt-1"):
                    for flow in flows:
                        self._card(flow)
            else:
                with ui.column().classes("w-full gap-0"):
                    for flow in flows:
                        self._row(flow)

    def _row(self, flow: Flow) -> None:
        """One flow in the list: name (opens it), a short line under it, ⚡ for triggers, Run / Edit / more."""
        with ui.row().classes("items-center no-wrap w-full gap-2 px-2 py-1 rounded hover:bg-primary/10"):
            ui.icon("account_tree").classes("text-primary")
            with ui.column().classes("gap-0 min-w-0 flex-1"):
                ui.link(flow.label, f"/flows/edit?flow={flow.name}").classes("font-medium no-underline truncate")
                inputs = ", ".join(i.name for i in flow.inputs)
                line = flow.description or f"{len(flow.nodes)} boxes" + (f" · inputs: {inputs}" if inputs else "")
                ui.label(line).classes("text-xs opacity-60 truncate w-full")
            if flow.triggers:
                ui.icon("bolt").classes("text-warning text-lg").tooltip("Also starts by itself: " + "; ".join(
                    f"{t.kind} " + ", ".join(f"{k} = {v}" for k, v in t.match.items()) for t in flow.triggers))
            button = ui.button(icon="play_arrow").props("flat round dense").tooltip("Run")
            button.on_click(lambda f=flow, b=button: self._run(f, b))
            ui.button(icon="edit").props(f"flat round dense href=/flows/edit?flow={flow.name}").tooltip("Edit")
            self._more(flow)

    def _more(self, flow: Flow) -> None:
        with ui.button(icon="more_vert").props("flat round dense"):
            with ui.menu():
                ui.menu_item("Move to folder", on_click=lambda f=flow: self._move(f))
                ui.menu_item("Duplicate", on_click=lambda f=flow: self._duplicate(f))
                ui.menu_item("Save as template", on_click=lambda f=flow: self._template(f))
                ui.menu_item("Export (download file)", on_click=lambda f=flow: self._export(f))
                ui.menu_item("Delete", on_click=lambda f=flow: self._delete(f))

    async def _move(self, flow: Flow) -> None:
        """Pick a folder from the list or type one (a new name makes a new folder)."""
        field = FolderField(self._library.folders(), flow.folder, "Folder (pick or type a new one)")
        with ui.dialog() as dialog, ui.card().classes("w-96 max-w-full gap-3"):
            ui.label(f"Move {flow.label} to").classes("font-semibold")
            field.build().classes("w-full")
            ui.label("Empty = No folder. Only the Flows page sorts by it: SAMMI, buttons and triggers keep "
                     "working.").classes("text-xs opacity-60")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat no-caps")
                ui.button("Move", on_click=lambda: dialog.submit(field.value)).props("unelevated no-caps")
        folder = await dialog
        dialog.delete()
        if folder is not None and folder != flow.folder:
            self._library.move(flow.name, folder)
            self.build.refresh()

    async def _new_folder(self) -> None:
        """A name and the flows to put in it (a folder only exists while a flow is in it)."""
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
            self.build.refresh()

    def _dissolve(self, folder: str) -> None:
        self._library.rename_folder(folder, "")
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

    def _card(self, flow: Flow) -> None:
        with ui.card().classes("w-full gap-2"):
            with ui.row().classes("items-center w-full gap-2"):
                ui.icon("account_tree").classes("text-xl text-primary")
                ui.label(flow.label).classes("text-lg font-semibold")
                if flow.triggers:
                    ui.badge(" · ".join(t.kind for t in flow.triggers)).props("color=warning text-color=black") \
                        .classes("text-xs").tooltip("Also starts by itself: " + "; ".join(
                            f"{t.kind} " + ", ".join(f"{k} = {v}" for k, v in t.match.items()) for t in flow.triggers))
                ui.space()
                button = ui.button("Run", icon="play_arrow").props("no-caps unelevated")
                button.on_click(lambda f=flow, b=button: self._run(f, b))
                ui.button("Edit", icon="edit").props(f"no-caps outline href=/flows/edit?flow={flow.name}")
                self._more(flow)
            if flow.description:
                ui.label(flow.description).classes("text-sm opacity-80")
            inputs = ", ".join(i.name + ("" if i.default is None else f" = {i.default}") for i in flow.inputs)
            ui.label(f"Action {flow.action_name}" + (f" · inputs: {inputs}" if inputs else "") +
                     " · SAMMI, Kit and the Live page can run it").classes("text-xs opacity-60")
            count = len(flow.nodes)
            # folded: a long flow would fill the page; the ⚡ badge above already says it has triggers
            with ui.expansion(f"Show boxes ({count})" + (" and triggers" if flow.triggers else ""), icon="list") \
                .props("dense").classes("w-full text-sm"):
                self._outline(flow, FlowOutline(flow, self._ports).build())
                for trigger in flow.triggers:
                    with ui.row().classes("items-center gap-1 text-sm pt-1"):
                        ui.icon("bolt").classes("text-warning")
                        ui.label(f"Also starts on {trigger.kind}: " +
                                 ", ".join(f"{k} = {v}" for k, v in trigger.match.items()))

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

    async def _import(self) -> None:
        with ui.dialog() as dialog, ui.card().classes("w-[28rem] max-w-full gap-3"):
            ui.label("Import flow").classes("text-lg font-semibold")
            ui.label("Pick a flow file (.toml) that was exported from a toolbox.").classes("text-sm opacity-80")

            async def uploaded(e) -> None:
                try:
                    text = (await e.file.read()).decode("utf-8")
                    flow = self._library.import_text(text, e.file.name)
                except Exception as error:
                    ui.notify(f"Not imported: {error}", type="negative", multi_line=True)
                    return
                dialog.submit(flow)

            ui.upload(on_upload=uploaded, auto_upload=True, max_files=1) \
                .props('accept=".toml" flat bordered label="Press + to pick the file, or drop it here"') \
                .classes("w-full")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("no-caps flat")
        flow = await dialog
        dialog.delete()
        if flow is None:
            return
        note = " (without its triggers: a flow with that name was there already)" \
            if flow.label.endswith("(imported)") else ""
        ui.notify(f"{flow.label} imported{note}", type="positive", multi_line=True)
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
