from collections.abc import Callable
from html import escape
from typing import Any

from streamer_toolbox.core.flows.box_wire import WIRE_IN, box_ref, box_source, is_wire_in
from streamer_toolbox.core.flows.flow_wire import START, FlowWire
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft
from streamer_toolbox.gui.components.flow_editor.node_draft import NodeDraft

START_ID = 1
BY_NAME = "*"  # the "by name" data dot: a result dropped there fills the fields named like its keys
# auto placement: columns leave room for the dot names outside the boxes; a column stacks by each box's height
LEFT, TOP, COLUMN, GAP = 20, 20, 330, 40
DOT, BOX = 32, 70  # one dot row (dot + gap), a box without dots

DataInputs = Callable[[NodeDraft], list[str]]
DataOutputs = Callable[[NodeDraft], list[tuple[str, str]]]


class DrawflowGraph:
    """Turns a flow into Drawflow's import data and reads the edited graph back.

    Run dots: every box has one input dot (left, the first), then one per entry (a Loop's "stop"; entries_of),
    and one output dot per port (right): one "done" dot, or "then" and "else" for an If. One output may be wired
    to several boxes: those run at the same time.
    Data dots (orange) come after them: on the left one per field that takes a wire (data_inputs_of), on the
    right the box's result or a Split box's fields (data_outputs_of). A data wire sets the field it ends at to
    ${box.<id>} / ${box.<id>.<field>}. A box without a saved spot is placed by how many wires it is from Start
    (columns), stacked when several share a column.
    """

    def __init__(self, ports_of: Callable[[str, dict], tuple[str, ...]], title_of: Callable[[str], str],
                 data_inputs_of: DataInputs = lambda node: [], data_outputs_of: DataOutputs = lambda node: [],
                 summary_of: Callable[[NodeDraft], str] | None = None,
                 start_outputs: Callable[[], list[tuple[str, str]]] = lambda: [],
                 entries_of: Callable[[NodeDraft], list[str]] = lambda node: []) -> None:
        self._ports_of = ports_of
        self._title_of = title_of
        self._data_inputs_of = data_inputs_of
        self._data_outputs_of = data_outputs_of
        self._start_outputs = start_outputs
        self._entries_of = entries_of
        self._summary_of = summary_of or (lambda node: ", ".join(
            f"{k} = {v}" for k, v in node.params.items() if v not in ("", None) and not is_wire_in(v)))

    def _dot_rows(self, node: NodeDraft) -> int:
        """How many dots the taller side of the box has (it grows with them)."""
        inputs = 1 + len(self._entries_of(node)) + len(self._data_inputs_of(node))
        outputs = len(self._ports_of(node.action, node.params)) + len(self._data_outputs_of(node))
        return max(inputs, outputs)

    @staticmethod
    def node_id(index: int) -> int:
        return index + 2

    def build(self, draft: FlowDraft) -> dict[str, Any]:
        spots = _default_spots(draft, {n.id: self._dot_rows(n) for n in draft.nodes})
        numbers = {START: START_ID} | {n.id: self.node_id(i) for i, n in enumerate(draft.nodes)}
        start_text = "button, SAMMI, Kit, API" + (", triggers" if draft.triggers else "")
        start_out = self._start_outputs()  # what started the flow: trigger data, flow inputs
        nodes = {str(START_ID): _node(START_ID, START, _html("Start", start_text), (LEFT, TOP), 0,
                                      1 + len(start_out), "tb-start")}
        nodes[str(START_ID)]["data"].update(ports=["out"], entries=[], data_in=[], data_out=[f for f, _ in start_out],
                                            labels_out=[label for _, label in start_out], tag="Start")
        for index, node in enumerate(draft.nodes):
            number = self.node_id(index)
            ports = self._ports_of(node.action, node.params)
            entries = self._entries_of(node)
            data_in = self._data_inputs_of(node)
            data_out = self._data_outputs_of(node)
            nodes[str(number)] = _node(number, node.id, self.html(node), node.box or spots[node.id],
                                       1 + len(entries) + len(data_in), len(ports) + len(data_out), self.css(node))
            # flow_boxes.js colours and labels the dots and wires; read() maps dots back by these names
            nodes[str(number)]["data"].update(ports=list(ports), entries=list(entries), data_in=data_in,
                                              data_out=[f for f, _ in data_out],
                                              labels_out=[label for _, label in data_out], tag=self._tag(node),
                                              port_labels=[_port_label(node, port) for port in ports])
        for wire in draft.wires:
            source, target = numbers.get(wire.source), numbers.get(wire.target)
            ports = self._ports(draft, wire.source)
            if source is None or target is None or wire.port not in ports:
                continue
            entries = nodes[str(target)]["data"].get("entries", [])
            if wire.entry and wire.entry not in entries:
                continue
            _connect(nodes, source, ports.index(wire.port) + 1, target,
                     2 + entries.index(wire.entry) if wire.entry else 1)
        for node in draft.nodes:  # data wires, from the fields that name a box
            target = nodes[str(numbers[node.id])]
            first = 2 + len(target["data"]["entries"])  # the first data dot
            for index, name in enumerate(target["data"]["data_in"]):
                wired = box_source(node.params.get(name))
                source = nodes.get(str(numbers.get(wired[0], 0))) if wired else None
                dot = _dot(source["data"], wired[1]) if source else None
                if dot is not None:
                    _connect(nodes, source["id"], dot, target["id"], index + first)
        return {"drawflow": {"Home": {"data": nodes}}}

    def html(self, node: NodeDraft) -> str:
        extra = f"→ {node.save_as}" if node.save_as else ""
        return _html(self._title_of(node.action) + ("" if node.enabled else " (off)"), self._summary_of(node),
                     node.note, extra)

    def _tag(self, node: NodeDraft) -> str:
        """How short wire ends name the box: "2 Split data"."""
        number = node.id[1:] if node.id[:1] == "n" and node.id[1:].isdigit() else node.id
        return f"{number} {self._title_of(node.action).split(' · ')[-1]}"

    @staticmethod
    def css(node: NodeDraft) -> str:
        return "tb-step" + ("" if node.enabled else " tb-off")

    def read(self, export: dict[str, Any], draft: FlowDraft) -> None:
        """Positions, deleted boxes and both kinds of wires, mapped by the dot names the graph was drawn with
        (the form may have changed a box's dots since)."""
        nodes = export["drawflow"]["Home"]["data"]
        by_number = {int(k): v["data"]["node"] for k, v in nodes.items()}
        kept = set(by_number.values())
        draft.nodes = [n for n in draft.nodes if n.id in kept]
        wires = []
        for number, data in nodes.items():
            source = by_number[int(number)]
            node = draft.node(source)
            if node is not None:
                node.box = (float(data["pos_x"]), float(data["pos_y"]))
            ports = data["data"].get("ports") or list(self._ports(draft, source))
            for output, links in data["outputs"].items():
                index = int(output.split("_")[1]) - 1
                if index >= len(ports):
                    continue
                for link in links["connections"]:
                    target = by_number.get(int(link["node"]))
                    dot = int(link["output"].split("_")[1])
                    entries = nodes.get(str(link["node"]), {}).get("data", {}).get("entries", [])
                    if not target or target == START or dot > 1 + len(entries):
                        continue  # a data dot
                    wires.append(FlowWire(source, ports[index], target, entries[dot - 2] if dot > 1 else ""))
            if node is not None:
                self._read_data_wires(data, node, nodes, by_number)
        draft.wires = list(dict.fromkeys(wires))

    @staticmethod
    def _read_data_wires(data: dict[str, Any], node: NodeDraft, nodes: dict[str, Any],
                         by_number: dict[int, str]) -> None:
        first = 2 + len(data["data"].get("entries", []))  # the first data dot
        for index, name in enumerate(data["data"].get("data_in", [])):
            if not is_wire_in(node.params.get(name)):
                continue  # switched to another source since it was drawn
            links = data["inputs"].get(f"input_{index + first}", {}).get("connections", [])
            value = WIRE_IN
            source = nodes.get(str(links[-1]["node"])) if links else None
            if source is not None:
                dot = int(links[-1]["input"].split("_")[1])
                ports, fields = source["data"].get("ports", []), source["data"].get("data_out", [])
                if len(ports) < dot <= len(ports) + len(fields):
                    value = box_ref(by_number[int(source["id"])], fields[dot - len(ports) - 1])
                    old = box_source(node.params.get(name))
                    if old and old[0] == by_number[int(source["id"])] and _dot(source["data"], old[1]) == dot:
                        value = node.params[name]  # e.g. ${box.n1.y} drawn from n1's result dot: keep the .y
            node.params[name] = value

    def _ports(self, draft: FlowDraft, node_id: str) -> tuple[str, ...]:
        if node_id == START:
            return ("out",)
        node = draft.node(node_id)
        return self._ports_of(node.action, node.params) if node else ()


def _dot(data: dict[str, Any], field: str) -> int | None:
    """The output dot number (from 1) that gives a field: its own dot on a Split box, else the result dot."""
    fields = data.get("data_out", [])
    offset = len(data.get("ports", []))
    if field in fields:
        return offset + fields.index(field) + 1
    return offset + fields.index("") + 1 if "" in fields else None


def _connect(nodes: dict[str, Any], source: int, output: int, target: int, input_: int) -> None:
    nodes[str(source)]["outputs"][f"output_{output}"]["connections"].append(
        {"node": str(target), "output": f"input_{input_}"})
    nodes[str(target)]["inputs"][f"input_{input_}"]["connections"].append(
        {"node": str(source), "input": f"output_{output}"})


def _default_spots(draft: FlowDraft, dot_rows: dict[str, int]) -> dict[str, tuple[float, float]]:
    depth: dict[str, int] = {}
    todo = [(START, 0)]
    while todo:
        current, level = todo.pop(0)
        for wire in draft.wires:
            if wire.source == current and wire.target not in depth:
                depth[wire.target] = level + 1
                todo.append((wire.target, level + 1))
    last = max(depth.values(), default=0) + 1
    tops: dict[int, float] = {}
    spots = {}
    for node in draft.nodes:
        column = depth.get(node.id, last)
        top = tops.get(column, TOP)
        tops[column] = top + max(BOX, DOT * dot_rows.get(node.id, 1)) + GAP
        spots[node.id] = (LEFT + COLUMN * column, top)
    return spots


def _node(number: int, node_id: str, html: str, pos: tuple[float, float], inputs: int, outputs: int,
          css: str) -> dict[str, Any]:
    return {"id": number, "name": node_id, "data": {"node": node_id}, "class": css, "html": html,
            "typenode": False,
            "inputs": {f"input_{i + 1}": {"connections": []} for i in range(inputs)},
            "outputs": {f"output_{i + 1}": {"connections": []} for i in range(outputs)},
            "pos_x": pos[0], "pos_y": pos[1]}


def _port_label(node: NodeDraft, port: str) -> str:
    """A Switch case's dot shows what it matches ("ra, right_arm"), other dots their name ("" = the name)."""
    value = node.params.get(port)
    if not isinstance(value, str) or not value.strip() or "${" in value:
        return ""
    return value if len(value) <= 18 else value[:17] + "…"


def _html(title: str, detail: str = "", note: str = "", extra: str = "") -> str:
    parts = [f'<div class="tb-title">{escape(title)}</div>']
    for text, css in ((detail, "tb-detail"), (extra, "tb-save"), (note, "tb-note")):
        if text:
            parts.append(f'<div class="{css}">{escape(text)}</div>')
    return "".join(parts)
