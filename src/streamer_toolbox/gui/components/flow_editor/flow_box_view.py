import json
from collections.abc import Awaitable, Callable

from nicegui import app, ui

from streamer_toolbox.core.flows.box_wire import WIRE_IN, box_source, is_wire_in
from streamer_toolbox.gui.components.flow_editor.wire_matcher import WireMatcher
from streamer_toolbox.core.flows.flow_wire import START
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
    Orange dots carry data: from a box's result (or a Split box's fields) into a field set to "Wire from a box",
    or into a box's "by name" dot, which wires each field named like one of the result's keys.
    Click a box to edit it in the panel on the left; the Delete key removes the selected box or wire.

    The graph lives in the browser while editing; sync() reads it back into the draft (wires, positions,
    deleted boxes). The page calls it before switching views and before saving."""

    def __init__(self, draft: FlowDraft, editor: NodeEditor,
                 test_run: Callable[[], Awaitable[None]] | None = None) -> None:
        self._draft = draft
        self._editor = editor
        self._graph = DrawflowGraph(editor.dots.ports, editor.dots.title, editor.dots.data_inputs, editor.dots.data_outputs,
                                    lambda node: editor.dots.summary(node, wired=False), editor.dots.start_outputs,
                                    editor.dots.entries)
        self._selected: str | None = None  # node id
        self._numbers: dict[int, str] = {}
        self._listening = False
        self._shown: str | None = None  # the debug marks on the page now
        self._test_run = test_run  # the editor's Test run (the Start box's panel offers it)
        self._start_open = False  # the Start box is clicked: its panel shows

    @staticmethod
    def add_head() -> None:
        ui.add_head_html(HEAD)

    def build(self) -> None:
        # the box form is a panel docked on the left, next to the canvas (never over a box); it slides in when a
        # box is clicked and folds to a thin strip with its buttons. Full screen: panel and canvas fill the screen
        with ui.element("div").props(f"id={AREA_ID}").classes("tb-flow-area relative flex no-wrap w-full"):
            with ui.element("div").props(f"id={PANEL_ID}").classes("tb-flow-panel"):
                with ui.row().classes("tb-flow-handle items-center no-wrap w-full px-2 py-1 gap-1 bg-primary "
                                      "text-white"):
                    ui.button(icon="chevron_left").on("click", js_handler=f"() => tbFlowPanel('{PANEL_ID}')") \
                        .props("flat round dense color=white size=sm").classes("tb-fold-button") \
                        .tooltip("Slide the panel in / out")
                    ui.label("Box").classes("tb-panel-title text-sm font-semibold flex-1")
                    ui.button(icon="add", on_click=self._add).props("flat round dense color=white size=sm") \
                        .classes("tb-rail-only").tooltip("Add box")
                    # this runs in the browser: full screen is only allowed straight from a click
                    ui.button(icon="fullscreen").on("click", js_handler=f"() => tbFlowFullscreen('{AREA_ID}')") \
                        .props("flat round dense color=white size=sm").classes("tb-full-button") \
                        .tooltip("Full screen on/off (Esc leaves it)")
                with ui.column().classes("tb-flow-body w-full gap-3 p-3"):
                    self.side_panel()
            ui.element("div").props(f"id={ELEMENT_ID}").classes("tb-drawflow flex-1 min-w-0 h-[640px]")
        ui.run_javascript(f"tbFlowPanelRestore('{PANEL_ID}')")
        with ui.row().classes("items-start no-wrap w-full gap-3 -mt-3"):
            ui.label("Drag the background to scroll · wire: drag from a right dot to a left dot · several wires "
                     "from one dot = at the same time · orange dots carry a value into a field (Wire from a box) · "
                     "click a box or wire, then Delete to remove it").classes("text-xs opacity-60 flex-1")
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
            ui.on("tb_flow_by_name", self._by_name)
            ui.on("tb_flow_key", self._key)
            self._listening = True
        self._draw()

    @ui.refreshable_method
    def side_panel(self) -> None:
        node = self._draft.node(self._selected) if self._selected else None
        with ui.row().classes("items-center w-full gap-2"):
            ui.button("Add box", icon="add", on_click=self._add).props("no-caps unelevated dense")
            if CLIPBOARD.has_box:
                ui.button("Paste", icon="content_paste", on_click=self._paste).props("no-caps flat dense") \
                    .tooltip("Adds the copied box (Ctrl+V on the canvas)")
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
        if node is not None:
            self._editor.build(node)
        elif self._start_open:
            self._start_panel()
        else:
            ui.label("Click a box to edit it. New boxes appear unwired: they run once a wire leads to them.") \
                .classes("text-xs opacity-60")

    def changed(self, rebuild: bool = False, edit: Callable[[], None] | None = None) -> None:
        """A box was edited in the side panel: redraw it (or everything, if its outputs may have changed). edit
        runs after the canvas was read back, before the redraw."""
        if rebuild or edit is not None:  # also without a selected box: a Split box that found its fields by itself
            ui.timer(0, lambda: self._resync(edit), once=True)
            return
        node = self._draft.node(self._selected) if self._selected else None
        if node is None:
            return
        number = self._number_of(node.id)
        ui.run_javascript(f"tbFlowUpdateNode({number}, {json.dumps(self._graph.html(node))}, "
                          f"{json.dumps(self._graph.css(node))})")

    async def sync(self) -> None:
        export = await ui.run_javascript("return window.tbFlow ? window.tbFlow.export() : null", timeout=5)
        if export:
            self._graph.read(export, self._draft)

    async def _resync(self, edit: Callable[[], None] | None = None) -> None:
        await self.sync()
        if edit is not None:
            edit()
        self._draw()
        self.side_panel.refresh()

    async def _add(self) -> None:
        action = await self._editor.picker().pick()
        if not action:
            return
        await self.sync()
        node: NodeDraft = self._draft.new_node(action)
        self._editor.prepare(node)
        self._selected = node.id
        self._draw()
        self.side_panel.refresh()
        ui.run_javascript(f"tbFlowPanel('{PANEL_ID}', true)")

    async def _copy(self, node_id: str) -> None:
        await self.sync()  # its spot as it is on the canvas now
        node = self._draft.node(node_id)
        if node is not None:
            CLIPBOARD.copy(node, self._draft.name)
            ui.notify(f"Copied {self._editor.dots.title(node.action)}", type="positive", timeout=1500)
            self.side_panel.refresh()

    async def _duplicate(self, node_id: str) -> None:
        await self.sync()
        node = self._draft.node(node_id)
        if node is not None:
            self._show_new(self._draft.add_copy(node, same_flow=True))

    async def _paste(self) -> None:
        taken = CLIPBOARD.take(self._draft.name)
        if taken is None:
            return
        await self.sync()
        original, same_flow = taken
        self._show_new(self._draft.add_copy(original, same_flow))
        if not same_flow and any(box_source(v) for v in original.params.values()):
            ui.notify("Pasted from another flow: its orange wires wait for new ones here", type="info")

    def _start_panel(self) -> None:
        """The Start box: what starts the flow, what the last start gave, and a test start with chosen values."""
        ui.label("Start").classes("text-base font-semibold")
        triggers = ", ".join(t.kind for t in self._draft.triggers)
        ui.label("Starts on its button, SAMMI, Kit, the API" + (f" and: {triggers}" if triggers else "") +
                 ". Its orange dots give what started it.").classes("text-xs opacity-70")
        if self._test_run:
            ui.button("Test run with values…", icon="play_circle", on_click=self._test_run) \
                .props("no-caps outline dense") \
                .tooltip("Choose what the trigger gives (user, input, reward, ...) and run the flow with it")
        ui.label("LAST START").classes("text-xs font-semibold uppercase tracking-wider text-primary pt-2")
        known, value = self._editor.dots.last_result(START)
        if known:
            ResultView.show(value)
        else:
            ui.label("Not started yet (since the toolbox started). Test run with values, or start it for real "
                     "(redeem, button, ...): then you see here exactly what it gives.").classes("text-xs opacity-70")

    def _show_new(self, node: NodeDraft) -> None:
        self._selected = node.id
        self._draw()
        self.side_panel.refresh()
        ui.run_javascript(f"tbFlowPanel('{PANEL_ID}', true)")

    async def _key(self, e) -> None:
        """Ctrl+C / Ctrl+V / Ctrl+D on the canvas (flow_boxes.js sends them)."""
        if e.args == "v":
            await self._paste()
        elif self._selected and e.args in ("c", "d"):
            await (self._copy if e.args == "c" else self._duplicate)(self._selected)

    async def _node_selected(self, e) -> None:
        node_id = self._numbers.get(e.args) if isinstance(e.args, int) else None
        self._selected = node_id if node_id != START else None
        self._start_open = node_id == START
        self.side_panel.refresh()
        if self._selected or self._start_open:
            ui.run_javascript(f"tbFlowPanel('{PANEL_ID}', true)")  # slide in to show the box

    async def _delete(self, node_id: str) -> None:
        await self.sync()  # moved boxes and new wires first
        node = self._draft.node(node_id)
        if node is not None:
            self._draft.remove(node_id, self._editor.dots.ports(node.action, node.params))
        self._selected = None
        self._draw()
        self.side_panel.refresh()

    def _close(self) -> None:
        self._selected = None
        self.side_panel.refresh()
        ui.run_javascript(f"tbFlowPanelClosed('{PANEL_ID}')")

    async def _node_removed(self, e) -> None:
        self._selected = None
        await self._resync()

    async def _data_wired(self, e) -> None:
        """A data wire was drawn or taken away: the field now names its box. A Split box that gets its data takes
        the keys the box before it is known to give (Video info: width, height, ...); if those aren't known and
        it has no fields yet, it reads the data."""
        await self.sync()
        node = self._draft.node(self._numbers.get(e.args)) if isinstance(e.args, int) else None
        action = self._editor.dots.action(node.action) if node else None
        if action and action.data_outputs and any(is_wire_in(v) and v != WIRE_IN for v in node.params.values()):
            if self._editor.dots.fields_from_wire(node):
                await self._resync()
                return
            if not node.params.get(action.data_outputs):
                await self._editor.find_fields(node)  # redraws through changed(rebuild=True) if it found some
        if node is not None and node.id == self._selected:
            self.side_panel.refresh()

    async def _by_name(self, e) -> None:
        """A result was dropped on a box's "by name" dot: each field named like one of its keys takes that key
        (Video info → Set source size: width and height). A field that already has a value or another wire
        keeps it; pick in its list to change it."""
        args = e.args if isinstance(e.args, dict) else {}
        target = self._draft.node(self._numbers.get(args.get("target")))
        source = self._numbers.get(args.get("source"))
        if target is None or source is None:
            return
        await self.sync()
        keys = await self._editor.result_keys(source, "" if source == START else args.get("field") or "")
        fields = self._editor.dots.fields(target)
        chosen, kept = WireMatcher.by_name(fields, source, keys, target.params)
        if not chosen and not kept:  # no field named like its keys (an If box): it becomes the first free value
            # the dot that was dropped, also from Start: ${box.start} alone has no dot, so no wire was drawn
            chosen = WireMatcher.as_value(fields, source, args.get("field") or "", target.params)
            if chosen:
                ui.notify(f"No field named like its keys: it's the value of {', '.join(chosen)} now",
                          type="positive", multi_line=True)
            else:
                ui.notify("Every field here already has a value or a wire: pick in a field to change it",
                          type="info", multi_line=True)
        elif chosen:
            ui.notify(f"Wired by name: {', '.join(chosen)}", type="positive")
        target.params.update(chosen)
        if kept:
            ui.notify(f"Kept as they were: {', '.join(kept)} (they have a value or another wire; pick in the "
                      "field to change)", type="info", multi_line=True)
        await self._resync()

    def _number_of(self, node_id: str) -> int:
        return next(number for number, n in self._numbers.items() if n == node_id)

    def _draw(self) -> None:
        data = self._graph.build(self._draft)
        self._numbers = {int(k): v["data"]["node"] for k, v in data["drawflow"]["Home"]["data"].items()}
        ui.run_javascript(f"tbFlowInit({json.dumps(ELEMENT_ID)}, {json.dumps(data)}, "
                          f"{json.dumps(self._short_wires())})")
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
        if self._start_open or self._selected:  # its Last start / Last result shows this run now
            self.side_panel.refresh()

    @staticmethod
    def _short_wires() -> bool:
        return bool(app.storage.general.get("flow_short_wires", True))

    @staticmethod
    def _set_short_wires(on: bool) -> None:
        app.storage.general["flow_short_wires"] = on
        ui.run_javascript(f"tbFlowSetShort({json.dumps(on)})")


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
