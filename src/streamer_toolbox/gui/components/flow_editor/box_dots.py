import inspect
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.numbered_fields import count_field
from streamer_toolbox.core.actions.registered_action import RegisteredAction
from streamer_toolbox.core.data.box_value import kind_of, understand
from streamer_toolbox.core.data.kind_check import KindCheck
from streamer_toolbox.core.data.value_helpers import HELPER, HELPERS, helpers_for
from streamer_toolbox.core.events.event_fields import EVENT_FIELDS
from streamer_toolbox.core.flows.box_wire import WIRE_IN, box_ref, box_source, is_wire_in
from streamer_toolbox.core.flows.flow_runner import PLACEHOLDER, FlowRunner
from streamer_toolbox.core.flows.flow_wire import DONE, START
from streamer_toolbox.gui.components.flow_editor.drawflow_graph import BY_NAME
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft
from streamer_toolbox.gui.components.flow_editor.node_draft import NodeDraft
from streamer_toolbox.gui.components.flow_editor.param_input import LIVE, field_label
from streamer_toolbox.gui.components.flow_editor.value_editors import EDITORS


class BoxDots:
    """What a box of the flow being edited takes and gives, without drawing anything: its action, run outputs
    and title, its fields, its data dots (orange: every field is a dot on the left, wired or not; the box's
    result, the keys it is known to have and a Value box's lines are dots on the right) with their kinds, the
    wires a field may take and the warnings for a wrong kind, and the one line that sums the box up. NodeEditor
    (the form) and the two views of the flow ask it."""

    def __init__(self, actions: ActionRegistry, runner: FlowRunner, draft: FlowDraft) -> None:
        self._actions = actions
        self._runner = runner
        self._draft = draft

    def action(self, name: str) -> RegisteredAction | None:
        return self._actions.get(name) if name in self._actions else None

    def data_only(self, node: NodeDraft) -> bool:
        """A box that only gives values: no run dots, no run wire (Value, Get variable)."""
        action = self.action(node.action)
        return bool(action and action.data_only)

    def ports(self, name: str, params: dict[str, Any] | None = None) -> tuple[str, ...]:
        action = self.action(name)
        return (action.ports_for(params or {}) if action else ()) or (DONE,)

    def title(self, name: str) -> str:
        action = self.action(name)
        return f"{action.category_title} · {action.title}" if action else name

    def entries(self, node: NodeDraft) -> list[str]:
        """The box's extra run dots on the left, after its normal one: a Loop's "stop", a run dot per line of a box
        with lines (Choose value's value_1, value_2, ...)."""
        action = self.action(node.action)
        return [*action.entries, *action.entry_lines(node.params)] if action else []

    def lines(self, name: str, params: dict[str, Any]) -> list[str]:
        """The run dots of a box with lines (Choose value, End), each starting it with its own value; else []."""
        action = self.action(name)
        return action.entry_lines(params) if action else []

    def lines_of(self, node: NodeDraft) -> list[str]:
        return self.lines(node.action, node.params)

    def data_inputs(self, node: NodeDraft) -> list[str]:
        """The orange dots on the left: "by name" (a box with fields; a result dropped there fills the fields
        named like its keys), then every field of the box in the action's order, wired or not (his round 45:
        inputs are always shown). Left out while they have no wire: a field the chosen way doesn't use, the
        number of a Switch's cases, and a Value box's lines. A box with lines has a field per line (value_1, ...)
        in place of the one its action takes (value)."""
        wired = [k for k, v in node.params.items() if is_wire_in(v)]
        action = self.action(node.action)
        if action is None:
            return wired
        leave = {action.value_lines, count_field(action.port_fields) if action.port_fields else ""}
        names = [k for k in self._fields(action, node)
                 if k in wired or (k not in leave and action.shows(k, node.params))]
        by_name = [BY_NAME] if self.fields(node) else []
        return by_name + names + [k for k in wired if k not in names]

    def fields(self, node: NodeDraft) -> list[str]:
        """The box's fields a wire can fill (none for a Value box: its lines are typed)."""
        action = self.action(node.action)
        if action is None or action.value_lines:
            return []
        return self._fields(action, node)

    @staticmethod
    def _fields(action: RegisteredAction, node: NodeDraft) -> list[str]:
        """The action's fields; a box with lines has its numbered ones in place of the one they stand for."""
        names = list(box_parameters(action))
        if action.entry_fields in names:
            at = names.index(action.entry_fields)
            names[at:at + 1] = action.entry_lines(node.params)
        return names

    def data_outputs(self, node: NodeDraft) -> list[tuple[str, str]]:
        """(field, label) per orange dot on the right: a Value box's lines, else one "result" dot for a box whose
        action gives something back (field "" = the whole result), followed by a dot for each key the result
        is known to have (Video info's width, height, ...)."""
        action = self.action(node.action)
        if action is None:
            return []
        if action.value_lines:
            return [(name, f"{name} · {kind}" if kind else name) for name, kind in self._line_kinds(node).items()]
        if not (_gives_result(action) or action.outputs):
            return []
        return [("", "result"), *((name, f"{name} · {kind}" if kind else name)
                                  for name, kind in action.outputs.items())]

    def known_outputs(self, node_id: str, field: str = "") -> dict[str, str]:
        """The keys (with kinds, "" if not known) that ${box.<node_id>.<field>} is known to have without running
        anything: a result's declared outputs, a Value box's lines, the Start box's fields."""
        if node_id == START:
            return {} if field else {name: "" for name, _ in self.start_outputs()}
        node = self._draft.node(node_id)
        action = self.action(node.action) if node else None
        if action is None or field:
            return {}
        if action.value_lines:
            return self._line_kinds(node)
        return dict(action.outputs)

    def start_outputs(self) -> list[tuple[str, str]]:
        """The Start box's orange dots: what its triggers give (user, message, ...), then the flow's inputs
        (the canvas sets them apart by their "(input)")."""
        inputs = {i.name: f"{i.name} (input)" for i in self._draft.inputs if i.name}
        given = {field: field for trigger in self._draft.triggers
                 for field in EVENT_FIELDS.get(trigger.kind, ()) if field not in inputs}
        return list((given | inputs).items())

    def output_kind(self, node_id: str, field: str) -> str:
        """The kind of one orange output ("" if not known): a Value line, a declared output or a helper; for
        the whole result what the action says it gives (-> str = text), else what it gave last time."""
        last = field.rsplit(".", 1)[-1]
        if last.startswith(HELPER):
            return HELPERS.get(last[1:], ("", "", None))[1]
        node = self._draft.node(node_id)
        action = self.action(node.action) if node else None
        if action is None:
            return ""
        if action.value_lines:
            return self._line_kinds(node).get(field, "")
        if field:
            return action.outputs.get(field, "")
        if action.outputs:
            return "object"
        kind = KindCheck.of_annotation(inspect.signature(action.handler).return_annotation)
        if kind != "any":
            return kind
        known, value = self.last_result(node_id)
        return kind_of(value) if known and value is not None else ""

    def wire_warnings(self, node: NodeDraft) -> dict[str, str]:
        """Field → warning, for wires that bring the wrong kind (text into a number field)."""
        action = self.action(node.action)
        parameters = box_parameters(action) if action else {}
        warnings = {}
        for name, value in node.params.items():
            source = box_source(value)
            if source and name in parameters:
                problem = KindCheck.problem(self.output_kind(*source),
                                            KindCheck.of_annotation(parameters[name].annotation))
                if problem:
                    warnings[name] = problem
        return warnings

    def wire_sources(self, node: NodeDraft) -> dict[str, str]:
        """Every other box's data dots, for "Wire from a box": ${box.n3} → "3 · Get model position", each also with
        its helpers (${box.n3.@keys} → "3 · Get model position · @keys = its keys")."""
        sources = {}
        for field, label in self.start_outputs():
            sources |= _with_helpers(box_ref(START, field), f"Start · {label}", self._start_kind(field))
        for other in self._draft.nodes:
            if other.id != node.id:
                title = f"{short_id(other.id)} · {self.title(other.action)}"
                for field, label in self.data_outputs(other):
                    sources |= _with_helpers(box_ref(other.id, field), f"{title} · {label}" if field else title,
                                             self.output_kind(other.id, field))
        return sources

    def _start_kind(self, field: str) -> str:
        """A Start dot's kind: a flow input's from its default, else from what the last start really gave. What a
        trigger gives (user, message, cost) is one plain value; an input without either isn't known."""
        for flow_input in self._draft.inputs:
            if flow_input.name == field and flow_input.default not in (None, ""):
                return kind_of(understand(flow_input.default))  # typed by hand
        known, started = self.last_result(START)
        if known and isinstance(started, dict) and started.get(field) not in (None, ""):
            return kind_of(understand(started[field]))  # what a viewer typed: 5 is a number
        return "" if any(i.name == field for i in self._draft.inputs) else "text"

    def field_name(self, node: NodeDraft, name: str) -> str:
        """A field's name on its row of the box: the one the form shows ("Compare with" for right)."""
        action = self.action(node.action)
        return (action.labels.get(name) if action else None) or field_label(name)

    def field_text(self, node: NodeDraft, name: str) -> str:
        """A field's value for its row on the box, in short; "" while it is empty or a wire brings it."""
        value = node.params.get(name)
        if value in ("", None) or is_wire_in(value):
            return ""
        action = self.action(node.action)
        if action and name in action.editors:  # a box's own value: in short ("3 steps · 2.5 s")
            return EDITORS[action.editors[name]].text(value)
        return self.value_text(value)

    def summary(self, node: NodeDraft, wired: bool = True, rows: bool = False) -> str:
        """The box's settings in one line; wired=False leaves out the fields a wire fills, rows=True the
        fields that have a row of their own on the box (the box view: every dot is a row)."""
        action = self.action(node.action)
        parts = [f"⚠ {k}: {w}" for k, w in self.wire_warnings(node).items()]
        own_rows = set(self.data_inputs(node)) if rows else set()
        for key, value in node.params.items():
            if value in ("", None) or (not wired and is_wire_in(value)) or key in own_rows:
                continue
            if action and not action.shows(key, node.params):  # a field the chosen way doesn't use
                continue
            if action and key in {count_field(f) for f in (action.port_fields, action.entry_fields) if f}:
                continue  # the dots show how many
            if action and key in action.editors:  # a box's own value: in short ("3 steps · 2.5 s")
                parts.append(f"{key} = {EDITORS[action.editors[key]].text(value)}")
            elif action and key == action.value_lines and isinstance(value, dict):
                parts += [f"{name} = {self.value_text(line)}" for name, line in value.items()]
            else:
                parts.append(f"{key} = {self.value_text(value)}")
        return ", ".join(parts)

    def value_text(self, value: Any) -> str:
        """A field's value for a box or list line: wires and Live values by name instead of ${...}."""
        if value == WIRE_IN:
            return "(not wired)"
        source = box_source(value)
        if source and source[0] == START:
            return f"⟵ Start · {source[1]}" if source[1] else "⟵ Start"
        if source:
            other = self._draft.node(source[0])
            name = self.title(other.action).split(" · ")[-1] if other else "?"
            return f"⟵ {short_id(source[0])} {name}" + (f" · {source[1]}" if source[1] else "")
        live = LIVE.fullmatch(value) if isinstance(value, str) else None
        if live:
            action = self.action(live.group(1))
            return f"⚡ {action.title if action else live.group(1)}{live.group(2)}"
        return str(value)

    def _line_kinds(self, node: NodeDraft) -> dict[str, str]:
        """A Value box's lines with their kinds: what a typed one holds ("" for one with ${...} in it)."""
        lines = node.params.get(self.action(node.action).value_lines)
        return {name: "" if isinstance(line, str) and PLACEHOLDER.search(line) else kind_of(understand(line))
                for name, line in lines.items()} if isinstance(lines, dict) else {}

    def last_result(self, node_id: str) -> tuple[bool, Any]:
        """(True, what the box gave last time: Test box, Test run or a real run) or (False, None)."""
        return self._runner.last_result(self._draft.name, node_id) if self._draft.name else (False, None)


def _with_helpers(ref: str, label: str, kind: str) -> dict[str, str]:
    """A data dot for the field's list, followed by the helpers that fit its kind:
    ${box.n3.@count} → "3 · Get rewards · @count = how many"."""
    return {ref: label} | {ref[:-1] + f".{HELPER}{name}}}": f"{label} · {HELPER}{name} = {HELPERS[name][0]}"
                           for name in helpers_for(kind)}


def short_id(node_id: str) -> str:
    """The number a box shows: "3" for n3."""
    return node_id[1:] if node_id[:1] == "n" and node_id[1:].isdigit() else node_id


def _gives_result(action: RegisteredAction) -> bool:
    """False for an action that gives nothing back (-> None) or picks an output (If, For each, Ask yes/no)."""
    if action.ports:
        return False
    returns = inspect.signature(action.handler).return_annotation
    return returns not in (None, "None", type(None)) and "AsyncIterator" not in str(returns)


def box_parameters(action: RegisteredAction) -> dict[str, inspect.Parameter]:
    return {p.name: p for p in inspect.signature(action.handler).parameters.values()
            if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)}
