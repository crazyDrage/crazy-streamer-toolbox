import json
from collections.abc import Awaitable, Callable
from dataclasses import asdict, replace

from nicegui import app, ui

from streamer_toolbox.core.flows.box_wire import box_source
from streamer_toolbox.core.flows.flow_group import COLORS, FlowGroup
from streamer_toolbox.core.flows.flow_wire import INPUT, START
from streamer_toolbox.gui.components.flow_editor.box_clipboard import CLIPBOARD
from streamer_toolbox.gui.components.flow_editor.drawflow_graph import DrawflowGraph
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft
from streamer_toolbox.gui.components.flow_editor.node_draft import NodeDraft
from streamer_toolbox.gui.components.flow_editor.node_editor import NodeEditor
from streamer_toolbox.gui.components.flow_editor.result_view import ResultView

ELEMENT_ID = "tb-drawflow"
AREA_ID = "tb-flow-area"
PANEL_ID = "tb-flow-panel"
HEAD = ('<link rel="stylesheet" href="/static/drawflow/drawflow.min.css">'
        '<link rel="stylesheet" href="/static/flow_boxes.css">'
        '<script src="/static/drawflow/drawflow.min.js"></script>'
        '<script src="/static/flow_boxes.js"></script>')


class FlowBoxView:
    """The flow as boxes with wires (Drawflow). Drag from a box's right dot to another box's left dot to wire
    them; several wires from one dot run those boxes at the same time; an If has a "then" and an "else" dot.
    Orange dots carry data: from a box's result (or one of its fields, or a Value box's lines) into a field set to
    "Wire from a box".
    Click a box to edit it in the panel on the left; the Delete key removes the selected box or wire. The boxes
    every flow has (Manual Start, a Start box per trigger, Input) show their own panel: start_form fills in what
    is set on them (a trigger's match, the inputs).

    The graph lives in the browser while editing; sync() reads it back into the draft (wires, positions,
    deleted boxes). The page calls it before switching views and before saving."""

    def __init__(self, draft: FlowDraft, editor: NodeEditor,
                 test_run: Callable[[str], Awaitable[None]] | None = None,
                 test_from: Callable[[str], Awaitable[None]] | None = None,
                 start_form: Callable[[str], None] = lambda box: None,
                 add_trigger: Callable[[], Awaitable[None]] | None = None) -> None:
        """test_run(start): a Test run from that Start box; add_trigger: the Add trigger window."""
        self._draft = draft
        self._editor = editor
        dots = editor.dots
        self._graph = DrawflowGraph(dots.ports, dots.title, dots.data_inputs, dots.data_outputs,
                                    lambda node: dots.summary(node, wired=False, rows=True),
                                    dots.start_outputs, dots.start_text, dots.entries, dots.field_text,
                                    dots.field_name, dots.data_only, dots.lines_of)
        self._start_form = start_form
        self._add_trigger = add_trigger
        self._selected: str | None = None  # node id
        self._group: str | None = None  # a group's title was clicked: its panel shows
        self._picked: list[str] = []  # several boxes picked at once (his round 83): Ctrl / Shift + click, a frame
        self._numbers: dict[int, str] = {}
        self._listening = False
        self._shown: str | None = None  # the debug marks on the page now
        self._test_run = test_run  # the editor's Test run (a Start box's panel offers it)
        self._test_from = test_from  # the editor's Test run from one box on (the right click menu)
        self._start: str | None = None  # a Start box or Input is clicked: its panel shows
        self._area: ui.element | None = None

    @staticmethod
    def add_head() -> None:
        ui.add_head_html(HEAD)

    def build(self) -> None:
        # the box form is a panel docked on the left, next to the canvas (never over a box); it slides in when a
        # box is clicked and folds to a thin strip with its buttons. Full screen: panel and canvas fill the screen
        with ui.element("div").props(f"id={AREA_ID}").classes("tb-flow-area relative flex no-wrap w-full") \
                as self._area:
            with ui.element("div").props(f"id={PANEL_ID}").classes("tb-flow-panel"):
                with ui.row().classes("tb-flow-handle items-center no-wrap w-full px-2 py-1 gap-1 bg-primary "
                                      "text-white"):
                    ui.button(icon="chevron_left").on("click", js_handler=f"() => tbFlowPanel('{PANEL_ID}')") \
                        .props("flat round dense color=white size=sm").classes("tb-fold-button") \
                        .tooltip("Slide the panel in / out")
                    ui.label("Box").classes("tb-panel-title text-sm font-semibold flex-1")
                    ui.button(icon="add", on_click=lambda: self._add()) \
                        .props("flat round dense color=white size=sm") \
                        .classes("tb-rail-only").tooltip("Add box")
                    # this runs in the browser: full screen is only allowed straight from a click
                    ui.button(icon="fullscreen").on("click", js_handler=f"() => tbFlowFullscreen('{AREA_ID}')") \
                        .props("flat round dense color=white size=sm").classes("tb-full-button") \
                        .tooltip("Full screen on/off (Esc leaves it)")
                with ui.column().classes("tb-flow-body w-full gap-3 p-3"):
                    self.side_panel()
            ui.element("div").props(f"id={ELEMENT_ID}").classes("tb-drawflow flex-1 min-w-0")
        ui.run_javascript(f"tbFlowPanelRestore('{PANEL_ID}')")
        with ui.row().classes("items-start no-wrap w-full gap-3 -mt-3"):
            ui.label("Drag the background to scroll · wire: drag from a right dot to a left dot · several wires "
                     "from one dot = at the same time · orange dots carry a value into a field (Wire from a box) · "
                     "click a box or wire, then Delete to remove it · Shift + click or Shift + drag picks several · "
                     "right click for a menu") \
                .classes("text-xs opacity-60 flex-1")
            ui.switch("Debug", value=self._debug(), on_change=lambda e: self._set_debug(e.value)) \
                .props("dense").classes("text-xs shrink-0") \
                .tooltip("Each box shows the full value it gave last time (Test run, Test box or a real run, "
                         "e.g. from SAMMI or a redeem), kept up to date while this is open")
            ui.switch("Long orange wires as short ends", value=self._short_wires(),
                      on_change=lambda e: self._set_short_wires(e.value)) \
                .props("dense").classes("text-xs shrink-0") \
                .tooltip("A long orange wire fades and its ends get a tag naming the other end. It still works; "
                         "hover it to see it")
        ui.timer(2.0, self._show_last)  # debug: values of a run started elsewhere (SAMMI, a redeem) show up
        if not self._listening:  # the page may build this view several times (view switch)
            ui.on("tb_flow_node", self._node_selected)
            ui.on("tb_flow_removed", self._node_removed)
            ui.on("tb_flow_wired", self._data_wired)
            ui.on("tb_flow_key", self._key)
            ui.on("tb_flow_menu", self._menu)
            ui.on("tb_flow_picked", self._picked_changed)
            ui.on("tb_flow_group", self._group_clicked)
            ui.on("tb_flow_group_folded", self._group_folded)
            self._listening = True
        self._draw()

    @ui.refreshable_method
    def side_panel(self) -> None:
        many = self._boxes() if len(self._picked) > 1 else []
        if len(many) > 1:
            self._many_panel(many)
            return
        group = self._draft.group(self._group) if self._group else None
        if group is not None:
            self._group_panel(group)
            return
        node = self._draft.node(self._selected) if self._selected else None
        with ui.row().classes("items-center w-full gap-2"):
            ui.button("Add box", icon="add", on_click=lambda: self._add()).props("no-caps unelevated dense")
            if self._add_trigger:
                ui.button("Add trigger", icon="bolt", on_click=self._add_trigger).props("no-caps outline dense") \
                    .tooltip("One more way the flow starts: its own Start box, wired like Start")
            if CLIPBOARD.has_box:
                ui.button("Paste", icon="content_paste", on_click=lambda: self._paste()) \
                    .props("no-caps flat dense") \
                    .tooltip("Adds the copied boxes (Ctrl+V on the canvas)")
            ui.space()
            if node is not None:
                ui.button(icon="library_add", on_click=lambda: self._duplicate(node.id)) \
                    .props("flat round dense").tooltip("Duplicate: a copy next to it (Ctrl+D)")
                ui.button(icon="content_copy", on_click=lambda: self._copy(node.id)) \
                    .props("flat round dense").tooltip("Copy, to paste here or in another flow (Ctrl+C)")
                ui.button("Delete box", icon="delete", on_click=lambda: self._delete(node.id)) \
                    .props("no-caps flat dense color=negative") \
                    .tooltip("Deletes this box. Wires before and after it are joined (like the list view)")
                ui.button(icon="close", on_click=self._close).props("flat round dense").tooltip("Close the panel")
            elif self._start is not None:
                if self._draft.trigger(self._start) is not None:
                    ui.button("Delete trigger", icon="delete", on_click=lambda: self._delete(self._start)) \
                        .props("no-caps flat dense color=negative") \
                        .tooltip("Takes this trigger and its Start box away")
                ui.button(icon="close", on_click=self._close).props("flat round dense").tooltip("Close the panel")
        if node is not None:
            self._editor.build(node)
        elif self._start is not None:
            self._start_panel(self._start)
        else:
            ui.label("Click a box to edit it. New boxes appear unwired: they run once a wire leads to them.") \
                .classes("text-xs opacity-60")

    def _many_panel(self, many: list[str]) -> None:
        """Several boxes picked (his round 83): what can be done with all of them at once."""
        with ui.row().classes("items-center w-full gap-2"):
            ui.label(f"{len(many)} boxes picked").classes("text-base font-semibold flex-1")
            ui.button(icon="close", on_click=lambda: ui.run_javascript("tbFlowPick([])"))                 .props("flat round dense").tooltip("Let them go")
        with ui.row().classes("items-center w-full gap-2"):
            ui.button("Duplicate", icon="library_add", on_click=lambda: self._duplicate())                 .props("no-caps outline dense").tooltip("Copies next to them, wired among themselves (Ctrl+D)")
            ui.button("Copy", icon="content_copy", on_click=lambda: self._copy())                 .props("no-caps outline dense").tooltip("To paste here or in another flow (Ctrl+C)")
            ui.button(f"Delete {len(many)} boxes", icon="delete", on_click=lambda: self._delete_many(self._boxes()))                 .props("no-caps flat dense color=negative")
        ui.label("Drag one of them to move them all. Ctrl / Shift + click adds or takes away a box; Shift + drag on "
                 "the empty canvas draws a frame around boxes.").classes("text-xs opacity-60")

    def _group_panel(self, group: FlowGroup) -> None:
        """A group (his round 83): its name, colour, folded or open. The boxes whose middle is inside it belong
        to it."""
        with ui.row().classes("items-center w-full gap-2"):
            ui.label("Group").classes("text-base font-semibold flex-1")
            ui.button("Delete group", icon="delete", on_click=lambda: self._delete_group(group.id)) \
                .props("no-caps flat dense color=negative").tooltip("Only the area goes; its boxes stay")
            ui.button(icon="close", on_click=self._close).props("flat round dense").tooltip("Close the panel")
        ui.input("Name", value=group.label,
                 on_change=lambda e: self._set_group(group.id, label=str(e.value or "").strip() or "Group")) \
            .props("dense").classes("w-full")
        with ui.row().classes("items-center gap-1"):
            for color in COLORS:
                ui.button(on_click=lambda c=color: self._set_group(group.id, color=c, redraw=True), color=None) \
                    .props("round dense unelevated size=sm") \
                    .classes(f"tb-group-swatch tb-group-{color}" + (" tb-swatch-on" if color == group.color else "")) \
                    .tooltip(color)
        ui.button("Open" if group.folded else "Fold", icon="unfold_more" if group.folded else "unfold_less",
                  on_click=lambda: self._set_group(group.id, folded=not group.folded, redraw=True)) \
            .props("no-caps outline dense")
        ui.label("Drag its title to move it with its boxes; drag its corner to make it bigger. A box belongs to it "
                 "when its middle is inside. Folded, it is one small box; its wires end at its edges. Only a view: "
                 "the flow runs the same.").classes("text-xs opacity-60")

    async def _group_clicked(self, e) -> None:
        group_id = e.args if isinstance(e.args, str) else None
        await self.sync()
        if self._draft.group(group_id) is None:
            return
        self._group, self._selected, self._start, self._picked = group_id, None, None, []
        self.side_panel.refresh()
        ui.run_javascript(f"tbFlowPanel('{PANEL_ID}', true)")

    async def _group_folded(self, e) -> None:
        if isinstance(e.args, str) and e.args == self._group:
            await self.sync()
            self.side_panel.refresh()

    async def _set_group(self, group_id: str, redraw: bool = False, **changes) -> None:
        await self.sync()
        self._draft.groups = [replace(g, **changes) if g.id == group_id else g for g in self._draft.groups]
        group = self._draft.group(group_id)
        if group is None:
            return
        ui.run_javascript(f"tbFlowGroupSet({json.dumps(_group_data(group))})")
        if redraw:
            self.side_panel.refresh()

    async def _add_group(self, spot: tuple[float, float]) -> None:
        await self.sync()
        group = self._draft.add_group(spot)
        self._group, self._selected, self._start, self._picked = group.id, None, None, []
        self._draw()
        self.side_panel.refresh()
        ui.run_javascript(f"tbFlowPanel('{PANEL_ID}', true)")

    async def _delete_group(self, group_id: str) -> None:
        await self.sync()
        self._draft.groups = [g for g in self._draft.groups if g.id != group_id]
        self._group = None
        self._draw()
        self.side_panel.refresh()

    def start_changed(self, box: str) -> None:
        """A trigger or the inputs changed in a form: that box shows it (its dots stay; a new dot needs
        changed(rebuild=True))."""
        if box in self._numbers.values():
            ui.run_javascript(f"tbFlowUpdateNode({self._number_of(box)}, {json.dumps(self._graph.start_html(box))}, "
                              f"{json.dumps(self._graph.start_css(box))})")

    def changed(self, rebuild: bool = False, edit: Callable[[], None] | None = None) -> None:
        """A box was edited in the side panel: redraw it (or everything, if its outputs may have changed). edit
        runs after the canvas was read back, before the redraw."""
        if rebuild or edit is not None:  # also without a selected box
            # in the view's own area: whoever asks may be gone by then (a trigger's row that was drawn again),
            # and a timer goes with the place it was made in
            with self._area:
                ui.timer(0, lambda: self._resync(edit), once=True)
            return
        node = self._draft.node(self._selected) if self._selected else None
        if node is None:
            return
        number = self._number_of(node.id)
        ui.run_javascript(f"tbFlowUpdateNode({number}, {json.dumps(self._graph.html(node))}, "
                          f"{json.dumps(self._graph.css(node))})")

    async def sync(self) -> None:
        state = await ui.run_javascript("return window.tbFlow ? {graph: window.tbFlow.export(), "
                                        "groups: window.tbFlowGroups || []} : null", timeout=5)
        if state and state.get("graph"):
            self._graph.read(state["graph"], self._draft)
            self._draft.groups = [_group_from(g) for g in state.get("groups") or [] if g.get("id")]

    async def _resync(self, edit: Callable[[], None] | None = None) -> None:
        await self.sync()
        if edit is not None:
            edit()
        self._draw()
        self.side_panel.refresh()

    async def _add(self, spot: tuple[float, float] | None = None) -> None:
        action = await self._editor.picker().pick()
        if not action or self._refused(action):
            return
        await self.sync()
        node: NodeDraft = self._draft.new_node(action)
        if spot is not None:
            node.box = spot
        self._editor.prepare(node)
        self._selected = node.id
        self._draw()
        self.side_panel.refresh()
        ui.run_javascript(f"tbFlowPanel('{PANEL_ID}', true)")

    def _boxes(self, node_id: str | None = None) -> list[str]:
        """The boxes an action is for: all picked ones when there are several (and node_id, if given, is one of
        them), else node_id or the selected box. Start boxes and Input aren't copied or duplicated."""
        picked = [n for n in self._picked if self._draft.node(n) is not None]
        if len(picked) > 1 and (node_id is None or node_id in picked):
            return picked
        one = node_id or self._selected
        return [one] if one and self._draft.node(one) is not None else []

    async def _copy(self, node_id: str | None = None) -> None:
        await self.sync()  # their spots as they are on the canvas now
        nodes = [self._draft.node(n) for n in self._boxes(node_id)]
        if nodes:
            CLIPBOARD.copy(nodes, self._draft.name, self._draft.wires)
            what = self._editor.dots.title(nodes[0].action) if len(nodes) == 1 else f"{len(nodes)} boxes"
            ui.notify(f"Copied {what}", type="positive", timeout=1500)
            self.side_panel.refresh()

    async def _duplicate(self, node_id: str | None = None) -> None:
        await self.sync()
        nodes = [self._draft.node(n) for n in self._boxes(node_id)]
        if nodes and not any(self._refused(n.action) for n in nodes):
            self._show_new(self._draft.add_copies(nodes, self._draft.wires, same_flow=True))

    def _refused(self, action: str) -> bool:
        """True (and says why) if the flow can't have one more box of this action (a second End)."""
        why = self._draft.refuses(self._editor.dots.action(action))
        if why:
            ui.notify(why, type="warning")
        return bool(why)

    async def _paste(self, spot: tuple[float, float] | None = None) -> None:
        taken = CLIPBOARD.take(self._draft.name)
        if taken is None:
            if spot is not None:  # asked for in the right click menu: say why nothing came
                ui.notify("Nothing copied yet: right click a box, then Copy", type="info")
            return
        originals, wires, same_flow = taken
        if any(self._refused(o.action) for o in originals):
            return
        await self.sync()
        self._show_new(self._draft.add_copies(originals, wires, same_flow, spot))
        inside = {o.id for o in originals}
        if not same_flow and any(box_source(v) and box_source(v)[0] not in inside
                                 for o in originals for v in o.params.values()):
            ui.notify("Pasted from another flow: its orange wires wait for new ones here", type="info")

    def _start_panel(self, box: str) -> None:
        """A Start box: what starts the flow there, what the last start gave, a test start with chosen values.
        Input: the flow's inputs."""
        ui.label(self._editor.dots.start_text(box)[0]).classes("text-base font-semibold")
        if box == INPUT:
            ui.label("What a button, the API or another flow (as a box) gives the flow. Each input is an orange dot "
                     "here; it has no run wire.").classes("text-xs opacity-70")
            self._start_form(box)
            return
        if box == START:
            ui.label("Starts on its button, SAMMI, Kit, the API or another flow (as a box). Each trigger has a "
                     "Start box of its own: Add trigger.").classes("text-xs opacity-70")
        else:
            ui.label("Starts when this happens. Its orange dots give what happened; a box wired to them gets "
                     "nothing when another Start box started the run.").classes("text-xs opacity-70")
            self._start_form(box)
        if self._test_run:
            ui.button("Test run with values…", icon="play_circle", on_click=lambda: self._test_run(box)) \
                .props("no-caps outline dense") \
                .tooltip("Runs the flow from this Start box, with values you choose")
        if box == START:
            return
        ui.label("LAST START").classes("text-xs font-semibold uppercase tracking-wider text-primary pt-2")
        known, value = self._editor.dots.last_result(box)
        if known:
            ResultView.show(value)
        else:
            ui.label("Not started yet (since the toolbox started). Test run with values, or start it for real "
                     "(redeem, chat, ...): then you see here exactly what it gives.").classes("text-xs opacity-70")

    def _show_new(self, nodes: list[NodeDraft]) -> None:
        """New boxes (pasted, duplicated): one opens in the panel, several stay picked to drag them at once."""
        self._selected = nodes[0].id if len(nodes) == 1 else None
        self._picked = [n.id for n in nodes] if len(nodes) > 1 else []
        self._draw()
        self.side_panel.refresh()
        if self._selected:
            ui.run_javascript(f"tbFlowPanel('{PANEL_ID}', true)")

    async def _key(self, e) -> None:
        """Ctrl+C / Ctrl+V / Ctrl+D on the canvas (flow_boxes.js sends them)."""
        if e.args == "v":
            await self._paste()
        elif e.args in ("c", "d"):
            await (self._copy if e.args == "c" else self._duplicate)()

    def _picked_changed(self, e) -> None:
        """The boxes picked on the canvas (flow_boxes.js: a list of box numbers)."""
        numbers = e.args if isinstance(e.args, list) else []
        picked = [self._numbers[n] for n in numbers if n in self._numbers]
        if picked != self._picked and (len(picked) > 1 or len(self._picked) > 1):
            self._picked = picked
            self.side_panel.refresh()
        self._picked = picked

    async def _menu(self, e) -> None:
        """A choice in the canvas's right click menu (flow_boxes.js): {do, node} for a box, {do, x, y} for a
        spot on the empty canvas."""
        args = e.args if isinstance(e.args, dict) else {}
        what = args.get("do")
        if what in ("add", "paste", "group"):
            spot = (float(args.get("x", 0)), float(args.get("y", 0)))
            await {"add": self._add, "paste": self._paste, "group": self._add_group}[what](spot)
            return
        node_id = self._numbers.get(args.get("node"))
        if node_id in self._editor.dots.start_boxes():
            if what == "test" and self._test_run:
                await self._test_run(node_id)
            elif what == "change":
                self._selected, self._start = None, node_id
                self.side_panel.refresh()
                ui.run_javascript(f"tbFlowPanel('{PANEL_ID}', true)")
            elif what == "delete":
                await self._delete(node_id)
            return
        if node_id is None or self._draft.node(node_id) is None:
            return
        if what == "change":
            self._selected, self._start = node_id, None
            self.side_panel.refresh()
            ui.run_javascript(f"tbFlowPanel('{PANEL_ID}', true)")
        elif what in ("copy", "duplicate"):
            await (self._copy if what == "copy" else self._duplicate)(node_id)
        elif what == "delete":
            await self._delete_many(self._boxes(node_id))
        elif what == "test_from" and self._test_from:
            await self._test_from(node_id)

    async def _node_selected(self, e) -> None:
        node_id = self._numbers.get(e.args) if isinstance(e.args, int) else None
        self._group = None
        start = node_id in self._editor.dots.start_boxes()
        self._selected = None if start else node_id
        self._start = node_id if start else None
        self.side_panel.refresh()
        if self._selected or self._start:
            ui.run_javascript(f"tbFlowPanel('{PANEL_ID}', true)")  # slide in to show the box

    async def _delete(self, node_id: str) -> None:
        await self.sync()  # moved boxes and new wires first
        node = self._draft.node(node_id)
        if node is not None:
            self._draft.remove(node_id, self._editor.dots.ports(node.action, node.params))
        elif self._draft.trigger(node_id) is not None:
            self._draft.remove_trigger(node_id)
        else:
            return  # Manual Start and Input stay
        self._selected = self._start = None
        self._draw()
        self.side_panel.refresh()

    async def _delete_many(self, node_ids: list[str]) -> None:
        if len(node_ids) <= 1:
            for node_id in node_ids:
                await self._delete(node_id)
            return
        await self.sync()
        for node_id in node_ids:
            node = self._draft.node(node_id)
            if node is not None:
                self._draft.remove(node_id, self._editor.dots.ports(node.action, node.params))
        self._selected = self._start = None
        self._picked = []
        self._draw()
        self.side_panel.refresh()

    def _close(self) -> None:
        self._selected = self._start = self._group = None
        self.side_panel.refresh()
        ui.run_javascript(f"tbFlowPanelClosed('{PANEL_ID}')")

    async def _node_removed(self, e) -> None:
        self._selected = None
        await self._resync()

    async def _data_wired(self, e) -> None:
        """A data wire was drawn or taken away: the field now names its box. When that changes the box's own
        dots (Object values: one per key of what is wired in), the canvas is drawn again, since only a new
        drawing makes dots (his round 81: the new dots were missing until the view was reloaded)."""
        node_id = self._numbers.get(e.args) if isinstance(e.args, int) else None
        dots = self._editor.dots
        node = self._draft.node(node_id) if node_id else None
        before = dots.data_outputs(node) if node is not None else None
        await self.sync()
        node = self._draft.node(node_id) if node_id else None
        if node is not None and dots.data_outputs(node) != before:
            self._draw()
        elif node is not None:
            self._show_wires(node)
        if node is not None and node.id == self._selected:
            self.side_panel.refresh()

    def _show_wires(self, node: NodeDraft) -> None:
        """A box after a wire came or went on the canvas: its rows (a wired field shows no value), and the
        canvas is told which of its fields have a wire now, as if it had been drawn like this."""
        boxes = self._graph.build(self._draft)["drawflow"]["Home"]["data"].values()
        box = next(b for b in boxes if b["data"]["node"] == node.id)
        ui.run_javascript(f"tbFlowUpdateNode({self._number_of(node.id)}, {json.dumps(box['html'])}, "
                          f"{json.dumps(self._graph.css(node))}, {json.dumps(box['data'].get('wired', {}))})")

    def _number_of(self, node_id: str) -> int:
        return next(number for number, n in self._numbers.items() if n == node_id)

    def _draw(self) -> None:
        data = self._graph.build(self._draft)
        self._numbers = {int(k): v["data"]["node"] for k, v in data["drawflow"]["Home"]["data"].items()}
        picked = [self._number_of(n) for n in self._picked if n in self._numbers.values()]
        groups = [_group_data(g) for g in self._draft.groups]
        ui.run_javascript(f"tbFlowInit({json.dumps(ELEMENT_ID)}, {json.dumps(data)}, "
                          f"{json.dumps(self._short_wires())}, {json.dumps(picked)}, {json.dumps(groups)})")
        self._shown = None  # a new canvas: debug marks go on again
        self._show_last()

    @staticmethod
    def _debug() -> bool:
        return bool(app.storage.general.get("flow_debug", False))

    def _set_debug(self, on: bool) -> None:
        app.storage.general["flow_debug"] = on
        self._shown = None
        self._show_last() if on else ui.run_javascript("tbFlowMark({})")

    def _show_last(self) -> None:
        """Debug: every box shows the full value it gave last time; only sent to the page when something changed."""
        if not self._debug():
            return
        text = self._last_marks()
        if text != self._shown:
            self._shown = text
            ui.run_javascript(f"tbFlowMark({text})")

    def _last_marks(self) -> str:
        marks = {}
        for number, node_id in self._numbers.items():
            known, value = self._editor.dots.last_result(node_id)
            if known:
                marks[number] = {"text": ResultView.text(value), "failed": False, "debug": True}
        return json.dumps(marks, sort_keys=True, default=str)

    def show_run(self, results: list[dict], failed: str | None, error: str) -> None:
        """After a Test run: each box shows what it gave (last time, if it ran more often), the failed one why."""
        marks: dict[int, dict] = {}
        for entry in results:
            node_id = entry.get("box")
            if node_id in self._numbers.values():
                if entry.get("skipped"):
                    text = "skipped (off)"
                else:
                    text = ResultView.text(entry.get("result")) if self._debug() else "✓ " + _short(entry.get("result"))
                marks[self._number_of(node_id)] = {"text": text.strip(), "failed": False, "debug": self._debug()}
        if failed in self._numbers.values():
            marks[self._number_of(failed)] = {"text": f"✗ {error}", "failed": True}
        ui.run_javascript(f"tbFlowMark({json.dumps(marks)})")
        self._shown = self._last_marks()  # debug: keep these (a failure shows why) until another run changes them
        if self._start or self._selected:  # its Last start / Last result shows this run now
            self.side_panel.refresh()

    @staticmethod
    def _short_wires() -> bool:
        return bool(app.storage.general.get("flow_short_wires", True))

    @staticmethod
    def _set_short_wires(on: bool) -> None:
        app.storage.general["flow_short_wires"] = on
        ui.run_javascript(f"tbFlowSetShort({json.dumps(on)})")


def _group_data(group: FlowGroup) -> dict:
    """A group as flow_boxes.js keeps it: {id, label, color, x, y, w, h, folded}."""
    data = asdict(group)
    (x, y), (w, h) = data.pop("box"), data.pop("size")
    return data | {"x": x, "y": y, "w": w, "h": h}


def _group_from(data: dict) -> FlowGroup:
    color = str(data.get("color", "blue"))
    return FlowGroup(str(data["id"]), str(data.get("label") or "Group"), color if color in COLORS else "blue",
                     (float(data.get("x", 0)), float(data.get("y", 0))),
                     (max(120.0, float(data.get("w", 420))), max(80.0, float(data.get("h", 280)))),
                     bool(data.get("folded", False)))


def _short(value) -> str:
    """A box's result in a few words for Test run."""
    if value is None:
        return ""
    if isinstance(value, dict):
        text = ", ".join(f"{k} = {round(v, 2) if isinstance(v, float) else v}" for k, v in value.items())
    elif isinstance(value, list):
        text = f"{len(value)} items"
    else:
        text = str(value)
    return text if len(text) <= 60 else text[:57] + "..."
