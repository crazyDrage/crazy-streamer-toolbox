from nicegui import ui

from streamer_toolbox.core.flows.box_wire import box_source
from streamer_toolbox.core.flows.flow_outline import FlowOutline
from streamer_toolbox.core.flows.flow_wire import START
from streamer_toolbox.core.flows.outline_entry import OutlineEntry
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft
from streamer_toolbox.gui.components.flow_editor.node_draft import NodeDraft
from streamer_toolbox.gui.components.flow_editor.node_editor import NodeEditor

PORT_LOOK = {"then": ("check_circle", "text-positive", "then (yes)"),
             "else": ("cancel", "text-negative", "else (no)")}


class FlowListView:
    """The flow as a list, like SAMMI: one line per box, top to bottom. Boxes that start together sit in an
    "At the same time" block, an If's outputs in "then" / "else" blocks. Open a line to edit the box."""

    def __init__(self, draft: FlowDraft, editor: NodeEditor) -> None:
        self._draft = draft
        self._editor = editor
        self._open: str | None = None

    @ui.refreshable_method
    def build(self) -> None:
        outline = FlowOutline(self._draft.to_flow(), self._editor.dots.ports)
        entries = outline.build()
        with ui.row().classes("items-center gap-2"):
            ui.icon("play_circle").classes("text-2xl text-positive")
            ui.label("Start").classes("font-semibold")
            ui.label("button, SAMMI, Kit, API" + (", triggers" if self._draft.triggers else "")) \
                .classes("text-xs opacity-60")
        with ui.column().classes("w-full gap-2 pl-3 border-l-2 border-positive/40"):
            self._entries(entries)
            self._add_button("Add box", entries, START, "out")
        loose = outline.loose()
        # a box no run wire reaches runs anyway when a field is wired to it (it gives a value)
        feeding = {s[0] for n in self._draft.nodes for s in map(box_source, n.params.values()) if s}
        for title, css, ids in (("Give values (run when a box needs them)", "text-primary",
                                 [i for i in loose if i in feeding]),
                                ("Not wired (these don't run)", "text-warning", [i for i in loose if i not in feeding])):
            if ids:
                ui.label(title).classes(f"text-sm font-semibold {css} pt-2")
            for node_id in ids:
                node = self._draft.node(node_id)
                if node is not None:
                    self._node(node)

    def _entries(self, entries: tuple[OutlineEntry, ...]) -> None:
        for entry in entries:
            if entry.kind == "parallel":
                with ui.column().classes("w-full gap-1 rounded-lg border border-primary/40 p-2"):
                    with ui.row().classes("items-center gap-1 text-primary"):
                        ui.icon("call_split")
                        ui.label("At the same time").classes("text-sm font-semibold")
                    for _, branch in entry.branches:
                        with ui.column().classes("w-full gap-2 pl-3 border-l-2 border-primary/40"):
                            self._entries(branch)
            elif entry.kind == "ref":
                node = self._draft.node(entry.node_id)
                with ui.row().classes("items-center gap-1 text-sm opacity-70 pl-2"):
                    ui.icon("subdirectory_arrow_right")
                    ui.label(f"goes on at box {_number(entry.node_id)} "
                             f"({self._editor.dots.title(node.action) if node else '?'}), shown above")
            else:
                node = self._draft.node(entry.node_id)
                if node is None:
                    continue
                self._node(node)
                for port, branch in entry.branches:
                    icon, colour, text = PORT_LOOK.get(port, ("arrow_right", "text-primary", port.replace("_", " ")))
                    case = node.params.get(port)  # a Switch case: what it matches
                    if isinstance(case, str) and case.strip():
                        text = f"{text}: {case}"
                    with ui.column().classes("w-full gap-2 pl-6"):
                        with ui.row().classes(f"items-center gap-1 {colour}"):
                            ui.icon(icon)
                            ui.label(text).classes("text-sm font-semibold")
                        with ui.column().classes("w-full gap-2 pl-3 border-l-2 border-gray-500/40"):
                            self._entries(branch)
                            self._add_button(f"Add to {port}", branch, node.id, port)

    def _node(self, node: NodeDraft) -> None:
        with ui.card().classes("w-full p-0 gap-0" + ("" if node.enabled else " opacity-60")):
            with ui.expansion(value=node.id == self._open).classes("w-full") as expansion:
                expansion.on_value_change(lambda e, n=node.id: self._opened(n, e.value))
                with expansion.add_slot("header"):
                    self._header(node)
                self._editor.build(node)

    def _header(self, node: NodeDraft) -> None:
        with ui.row().classes("items-center no-wrap gap-2 w-full"):
            ui.badge(_number(node.id)).props("color=primary rounded").tooltip(f"box {node.id}")
            with ui.column().classes("gap-0 min-w-0 flex-1"):
                ui.label(self._editor.dots.title(node.action) + ("" if node.enabled else "  (off)")).classes("font-medium")
                summary = self._editor.dots.summary(node)
                if summary:
                    ui.label(summary).classes("text-xs opacity-70 break-all")
                if node.save_as:
                    ui.label(f"→ saved in variable {node.save_as}").classes("text-xs text-primary")
                if node.note:
                    ui.label(node.note).classes("text-xs text-warning")
            ports = self._editor.dots.ports(node.action, node.params)
            tools = []
            if len(ports) == 1:
                tools.append(("add", "Add a box after this one", lambda: self._add(node.id, ports[0])))
            tools += [("call_split", "Add a box that runs at the same time", lambda: self._add_beside(node.id)),
                      ("delete", "Delete this box", lambda: self._delete(node))]
            for icon, tip, handler in tools:
                ui.button(icon=icon, on_click=handler).props("flat round dense").tooltip(tip) \
                    .classes("max-sm:hidden").on("click.stop", lambda: None)
            with ui.button(icon="more_vert").props("flat round dense").classes("sm:hidden") \
                    .on("click.stop", lambda: None):
                with ui.menu():
                    for icon, tip, handler in tools:
                        ui.menu_item(tip, on_click=handler)

    def _add_button(self, text: str, entries: tuple[OutlineEntry, ...], source: str, port: str) -> None:
        """Adds at the end of that list: after its last box, or right after source/port if it's empty. After a
        block (parallel or If) there's no single end, so the button is left out there."""
        if entries:
            last = entries[-1]
            node = self._draft.node(last.node_id) if last.kind == "node" else None
            ports = self._editor.dots.ports(node.action, node.params) if node else ()
            if len(ports) != 1:
                return
            source, port = last.node_id, ports[0]
        ui.button(text, icon="add", on_click=lambda: self._add(source, port)) \
            .props("no-caps dense outline").classes("self-start")

    async def _add(self, source: str, port: str) -> None:
        action = await self._editor.picker().pick()
        if action:
            node = self._draft.add_after(source, port, action, self._editor.dots.ports(action)[0])
            self._editor.prepare(node)
            self._open = node.id
            self.build.refresh()

    async def _add_beside(self, node_id: str) -> None:
        action = await self._editor.picker().pick("Add a box that runs at the same time")
        if action:
            node = self._draft.add_beside(node_id, action)
            self._editor.prepare(node)
            self._open = node.id
            self.build.refresh()

    def _delete(self, node: NodeDraft) -> None:
        self._draft.remove(node.id, self._editor.dots.ports(node.action, node.params))
        self.build.refresh()

    def _opened(self, node_id: str, value: bool) -> None:
        if value:
            self._open = node_id
        elif self._open == node_id:
            self._open = None


def _number(node_id: str) -> str:
    return node_id[1:] if node_id[:1] == "n" and node_id[1:].isdigit() else node_id
