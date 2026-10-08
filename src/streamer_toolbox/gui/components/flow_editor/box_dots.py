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
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_wire import DONE, START
from streamer_toolbox.gui.components.flow_editor.drawflow_graph import BY_NAME
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft
from streamer_toolbox.gui.components.flow_editor.node_draft import NodeDraft
from streamer_toolbox.gui.components.flow_editor.param_input import LIVE
from streamer_toolbox.gui.components.flow_editor.value_editors import EDITORS


class BoxDots:
    """What a box of the flow being edited takes and gives, without drawing anything: its action, run outputs
    and title, its fields, its data dots (orange: a field wired from another box is a dot on the left, the box's
    result or a Split box's fields are dots on the right) with their kinds, the wires a field may take and the
    warnings for a wrong kind, and the one line that sums the box up. NodeEditor (the form) and the two views of
    the flow ask it."""

    def __init__(self, actions: ActionRegistry, runner: FlowRunner, draft: FlowDraft) -> None:
        self._actions = actions
        self._runner = runner
        self._draft = draft

    def action(self, name: str) -> RegisteredAction | None:
        return self._actions.get(name) if name in self._actions else None

    def ports(self, name: str, params: dict[str, Any] | None = None) -> tuple[str, ...]:
        action = self.action(name)
        return (action.ports_for(params or {}) if action else ()) or (DONE,)

    def title(self, name: str) -> str:
        action = self.action(name)
        return f"{action.category_title} · {action.title}" if action else name

    def entries(self, node: NodeDraft) -> list[str]:
        """The box's extra run dots on the left, after its normal one (a Loop's "stop")."""
        action = self.action(node.action)
        return list(action.entries) if action else []

    def data_inputs(self, node: NodeDraft) -> list[str]:
        """The orange dots on the left: "by name" (a box with fields; a result dropped there fills the fields
        named like its keys), then the fields that take a data wire, in the action's order."""
        action = self.action(node.action)
        order = list(box_parameters(action)) if action else []
        wired = [k for k, v in node.params.items() if is_wire_in(v)]
        by_name = [BY_NAME] if self.fields(node) else []
        return by_name + sorted(wired, key=lambda k: order.index(k) if k in order else len(order))

    def fields(self, node: NodeDraft) -> list[str]:
        """The box's fields a wire can fill (none for a Split box: its data field is a dot already)."""
        action = self.action(node.action)
        if action is None or action.data_outputs:
            return []
        return list(box_parameters(action))

    def data_outputs(self, node: NodeDraft) -> list[tuple[str, str]]:
        """(field, label) per orange dot on the right: a Split box's fields, else one "result" dot for a box whose
        action gives something back (field "" = the whole result). A result's keys (Video info's width, ...)
        have no dots of their own: a field picks one in its list, or the result goes to a "by name" dot."""
        action = self.action(node.action)
        if action is None:
            return []
        if action.data_outputs:
            fields = node.params.get(action.data_outputs)
            return [(name, f"{name} · {kind}") for name, kind in fields.items()] if isinstance(fields, dict) else []
        return [("", "result")] if _gives_result(action) or action.outputs else []

    def known_outputs(self, node_id: str, field: str = "") -> dict[str, str]:
        """The keys (with kinds, "" if not known) that ${box.<node_id>.<field>} is known to have without running
        anything: a result's declared outputs, a Split box's fields, the Start box's fields."""
        if node_id == START:
            return {} if field else {name: "" for name, _ in self.start_outputs()}
        node = self._draft.node(node_id)
        action = self.action(node.action) if node else None
        if action is None or field:
            return {}
        if action.data_outputs:
            fields = node.params.get(action.data_outputs)
            return dict(fields) if isinstance(fields, dict) else {}
        return dict(action.outputs)

    def start_outputs(self) -> list[tuple[str, str]]:
        """The Start box's orange dots: the flow's inputs, then what its triggers give (user, message, ...)."""
        outputs = {i.name: f"{i.name} (input)" for i in self._draft.inputs if i.name}
        for trigger in self._draft.triggers:
            for field in EVENT_FIELDS.get(trigger.kind, ()):
                outputs.setdefault(field, field)
        return list(outputs.items())

    def output_kind(self, node_id: str, field: str) -> str:
        """The kind of one orange output ("" if not known): a Split field, a declared output or a helper; for
        the whole result what the action says it gives (-> str = text), else what it gave last time."""
        last = field.rsplit(".", 1)[-1]
        if last.startswith(HELPER):
            return HELPERS.get(last[1:], ("", "", None))[1]
        node = self._draft.node(node_id)
        action = self.action(node.action) if node else None
        if action is None:
            return ""
        if action.data_outputs:
            fields = node.params.get(action.data_outputs)
            return fields.get(field, "") if field and isinstance(fields, dict) else ""
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
                action = self.action(other.action)
                if action and not action.data_outputs:  # the result's keys: no dots, but in the list
                    for field, kind in action.outputs.items():
                        sources[box_ref(other.id, field)] = f"{title} · {field}" + (f" · {kind}" if kind else "")
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

    def summary(self, node: NodeDraft, wired: bool = True) -> str:
        """The box's settings in one line; wired=False leaves out the fields that have a dot."""
        action = self.action(node.action)
        parts = [f"⚠ {k}: {w}" for k, w in self.wire_warnings(node).items()]
        for key, value in node.params.items():
            if value in ("", None) or (not wired and is_wire_in(value)):
                continue
            if action and not action.shows(key, node.params):  # a field the chosen way doesn't use
                continue
            if action and action.port_fields and key == count_field(action.port_fields):
                continue  # the dots show how many
            if action and key in action.editors:  # a box's own value: in short ("3 steps · 2.5 s")
                parts.append(f"{key} = {EDITORS[action.editors[key]].text(value)}")
            elif action and key == action.data_outputs:
                if wired:  # the box view shows them as dots
                    parts.append(f"{key}: {', '.join(value) if isinstance(value, dict) else value}")
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

    def fields_from_wire(self, node: NodeDraft) -> bool:
        """Split data: takes its outputs from what the box wired in is known to give (Video info → width,
        height, ...), without running anything. False if that isn't known (Find fields then reads a sample)."""
        action = self.action(node.action)
        source = box_source(next((v for k, v in node.params.items() if action and k != action.data_outputs), ""))
        known = self.known_outputs(*source) if source else {}
        if not known:
            return False
        node.params[action.data_outputs] = {name: kind or "any" for name, kind in known.items()}
        return True

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
