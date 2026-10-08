import inspect
from collections.abc import Callable
from typing import Any

from nicegui import ui

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.box_filter_store import BoxFilterStore
from streamer_toolbox.core.actions.numbered_fields import count_field, numbered_fields
from streamer_toolbox.core.actions.registered_action import RegisteredAction
from streamer_toolbox.core.data.box_value import kind_of, understand
from streamer_toolbox.core.data.value_helpers import HELPER, HELPERS, helpers_for
from streamer_toolbox.core.data.kind_check import KindCheck
from streamer_toolbox.core.events.event_fields import EVENT_FIELDS
from streamer_toolbox.core.files.box_value_files import BoxValueFiles
from streamer_toolbox.core.flows.box_wire import WIRE_IN, box_ref, box_source, field_of, is_wire_in
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_wire import DONE, START
from streamer_toolbox.core.variables.variable_store import VariableStore
from streamer_toolbox.gui.components.flow_editor.action_picker import ActionPicker, SwitchedOff
from streamer_toolbox.gui.components.flow_editor.animation_input import AnimationInput
from streamer_toolbox.gui.components.flow_editor.drawflow_graph import BY_NAME
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft
from streamer_toolbox.gui.components.flow_editor.node_draft import NodeDraft
from streamer_toolbox.gui.components.flow_editor.param_input import LIVE, VAR, ParamInput
from streamer_toolbox.gui.components.flow_editor.placement_input import PlacementInput
from streamer_toolbox.gui.components.flow_editor.result_view import ResultView
from streamer_toolbox.gui.components.flow_editor.split_fields_input import SplitFieldsInput
from streamer_toolbox.gui.components.flow_editor.wire_by_name_dialog import WireByNameDialog


class NodeEditor:
    """The form for one box: its action (Change opens the Add menu), each parameter (value, variable, Live value,
    flow input or a wire from another box), "save result in variable", on/off, note, and the Test and Save current
    buttons. It also knows each box's data dots (orange): a field wired from another box is a dot on the left, the
    box's result (or a Split box's fields) are dots on the right.

    on_change() after an edit; on_change(rebuild=True) when the box's outputs or form changed shape."""

    def __init__(self, actions: ActionRegistry, runner: FlowRunner, variables: VariableStore,
                 box_files: BoxValueFiles, draft: FlowDraft, on_change: Callable[..., None],
                 box_filters: BoxFilterStore | None = None, switched_off: SwitchedOff | None = None) -> None:
        self._actions = actions
        self._runner = runner
        self._variables = variables
        self._box_files = box_files
        self._draft = draft
        self._on_change = on_change
        self._box_filters = box_filters
        self._switched_off = switched_off

    def picker(self) -> ActionPicker:
        return ActionPicker(self._actions, f"flow.{self._draft.name}" if self._draft.name else "",
                            self._box_filters, self._switched_off)

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
        order = list(_parameters(action)) if action else []
        wired = [k for k, v in node.params.items() if is_wire_in(v)]
        by_name = [BY_NAME] if self.fields(node) else []
        return by_name + sorted(wired, key=lambda k: order.index(k) if k in order else len(order))

    def fields(self, node: NodeDraft) -> list[str]:
        """The box's fields a wire can fill (none for a Split box: its data field is a dot already)."""
        action = self.action(node.action)
        if action is None or action.data_outputs:
            return []
        return list(_parameters(action))

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
        parameters = _parameters(action) if action else {}
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

    def prepare(self, node: NodeDraft) -> None:
        """A new box: a Split box's data comes in by wire, so it starts with that dot; a Switch with two cases."""
        action = self.action(node.action)
        if action and action.port_fields:
            node.params.setdefault(count_field(action.port_fields), 2)
        if action and action.data_outputs:
            for name, parameter in _parameters(action).items():
                if name != action.data_outputs and parameter.default is inspect.Parameter.empty:
                    node.params.setdefault(name, WIRE_IN)

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

    async def find_fields(self, node: NodeDraft) -> None:
        """Split data: one output per field of the data wired in, with its kind: what the box before it is known
        to give, else read from the data now."""
        action = self.action(node.action)
        if self.fields_from_wire(node):
            ui.notify(f"Fields: {', '.join(node.params[action.data_outputs])}", type="positive")
            self._on_change(rebuild=True)
            return
        data = next((v for k, v in node.params.items() if action and k != action.data_outputs), "")
        try:
            found, value = await self._sample(data)
        except Exception as e:  # service not connected, ...
            ui.notify(f"Can't read the data now: {e}", type="warning", multi_line=True)
            return
        if not found:
            ui.notify("Nothing to read yet: run the flow (or Test the box that gives the data) first, or add the "
                      "fields by hand", type="warning", multi_line=True)
            return
        value = understand(value)
        if not isinstance(value, dict):
            ui.notify(f"The data isn't an object with fields: {str(value)[:80]}", type="warning")
            return
        node.params[action.data_outputs] = {k: kind_of(v) for k, v in value.items()}
        ui.notify(f"Found {len(value)} fields: {', '.join(value)}", type="positive")
        self._on_change(rebuild=True)

    async def result_keys(self, node_id: str, field: str = "") -> list[str]:
        """The keys of what ${box.<node_id>.<field>} gives: known ones, else from a sample (last run, Live
        value). Empty if neither tells."""
        known = self.known_outputs(node_id, field)
        if known:
            return list(known)
        try:
            found, value = await self._sample(box_ref(node_id, field))
        except Exception:  # service not connected, ...
            return []
        value = understand(value) if found else None
        return list(value) if isinstance(value, dict) else []

    async def _sample(self, value: Any) -> tuple[bool, Any]:
        """What a field would get now: a Live value or variable is read; a wire gives the box's last result, or
        reads it now if that box is a Live value (Get model position)."""
        source = box_source(value)
        if source and source[0] == START:  # what started the last run
            found, started = self._runner.last_result(self._draft.name, START)
            return (True, field_of(started, source[1], "Start")) if found else (False, None)
        if source:
            node = self._draft.node(source[0])
            action = self.action(node.action) if node else None
            if node is None:
                return False, None
            if action and action.live:
                found, result = True, await self._actions.run(node.action)
            elif action and action.data_outputs:  # Split after Split: what the first one's data holds
                found, result = await self._sample(next((v for k, v in node.params.items()
                                                         if k != action.data_outputs), ""))
            else:
                found, result = self._runner.last_result(self._draft.name, node.id)
            return (True, field_of(result, source[1], f"box {node.id}")) if found else (False, None)
        live = LIVE.fullmatch(value) if isinstance(value, str) else None
        if live:
            return True, field_of(await self._actions.run(live.group(1)), live.group(2), live.group(1))
        variable = VAR.fullmatch(value) if isinstance(value, str) else None
        if variable:
            return True, self._variables.lookup(variable.group(1) + variable.group(2))
        return value not in ("", None, WIRE_IN), value

    def build(self, node: NodeDraft) -> None:
        action = self.action(node.action)
        with ui.row().classes("items-center no-wrap gap-2 w-full"):
            with ui.column().classes("gap-0 flex-1 min-w-0"):
                ui.label(self.title(node.action)).classes("font-medium")
                ui.label(action.description if action else "Unknown action: its connection or plugin isn't "
                         "loaded").classes("text-xs " + ("opacity-70" if action else "text-negative"))
            ui.button("Change", icon="swap_horiz", on_click=lambda: self._change(node)).props("no-caps flat dense")
        parameters = _parameters(action) if action is not None else {}
        if parameters:
            _section("Settings")
            live = {a.name: f"{a.category_title} · {a.title}" for a in self._actions.live()}
            sources = self.wire_sources(node)
            warnings = self.wire_warnings(node)
            shown = {n: p for n, p in parameters.items() if action.shows(n, node.params)}
            choosers = action.choosers()
            for index, (name, parameter) in enumerate(shown.items()):
                if index:
                    ui.separator().classes("opacity-40")
                if name == action.data_outputs:
                    fields = node.params.get(name)
                    SplitFieldsInput(fields if isinstance(fields, dict) else {}, lambda: self.find_fields(node),
                                     lambda value, n=name: self._set_param(node, n, value, rebuild=True)).build()
                    continue
                if name in action.editors:  # a value the box keeps itself, edited in its own window
                    EDITORS[action.editors[name]](
                        action.labels.get(name, ""), node.params.get(name), self._actions, self._box_files,
                        lambda value, n=name: self._set_param(node, n, value), node.params).build()
                    continue
                default = None if parameter.default is inspect.Parameter.empty else parameter.default
                value = node.params.get(name, "")
                if name in choosers and value in ("", None):  # a chooser shows the way that's in use
                    value = default
                ParamInput(name, default, value, parameter.annotation, action.options.get(name),
                           self._variables, [i.name for i in self._draft.inputs], live, self._actions.run, sources,
                           lambda value, rebuild, n=name: self._set_param(node, n, value, rebuild or n in choosers),
                           warnings.get(name, ""), action.labels.get(name, ""), _hint(action, name, node),
                           action.files.get(name), name in action.colors, action.many.get(name),
                           action.lights.get(name)).build()
            if action.port_fields:
                self._numbered(node, action, live, sources, warnings)
        _section("Result")
        names = sorted(set(self._variables.names()) | ({node.save_as} if node.save_as else set()), key=str.casefold)
        ui.select(names, value=node.save_as or None, label="save it in a variable (optional)",
                  new_value_mode="add-unique", clearable=True,
                  on_change=lambda e: self._set(node, "save_as", e.value or "")) \
            .props("outlined dense options-dense").classes("w-full")
        self._last_result(node)
        _section("Box")
        with ui.row().classes("items-center no-wrap gap-2 w-full"):
            ui.switch("On", value=node.enabled, on_change=lambda e: self._set(node, "enabled", e.value))
            ui.input(placeholder="note (shows on the box)", value=node.note,
                     on_change=lambda e: self._set(node, "note", e.value)) \
                .props("outlined dense").classes("flex-1")
        with ui.row().classes("gap-2 pt-1"):
            test = ui.button("Test box", icon="play_arrow").props("no-caps outline dense")
            test.on_click(lambda: self._test(node, test))
            if parameters:
                ui.button("Wire by name", icon="cable", on_click=lambda: self._wire_by_name(node, action)) \
                    .props("no-caps outline dense").tooltip("Wire this box's fields to outputs with the same name")
            if action and action.capture and action.shows(action.capture.partition(":")[2], node.params):
                ui.button("Save current", icon="my_location", on_click=lambda: self._capture(node, action)) \
                    .props("no-caps outline dense").tooltip(self._capture_tip(action))

    def _numbered(self, node: NodeDraft, action: RegisteredAction, live: dict[str, str], sources: dict[str, str],
                  warnings: dict[str, str]) -> None:
        """A Switch's cases: one field each (with x to take it and its output away) and "+ Add case"."""
        prefix = action.port_fields
        names = numbered_fields(prefix, node.params)
        for number, name in enumerate(names, 1):
            ui.separator().classes("opacity-40")
            with ui.row().classes("items-start no-wrap w-full gap-1"):
                with ui.column().classes("flex-1 min-w-0"):
                    ParamInput(name, None, node.params.get(name, ""), str, None, self._variables,
                               [i.name for i in self._draft.inputs], live, self._actions.run, sources,
                               lambda value, rebuild, n=name: self._set_param(node, n, value, rebuild),
                               warnings.get(name, ""), hint=action.hints.get(prefix, "") if number == 1 else "").build()
                if len(names) > 1:
                    ui.button(icon="close", on_click=lambda n=number: self._on_change(
                        rebuild=True, edit=lambda: self._draft.remove_numbered(node.id, prefix, n))) \
                        .props("flat round dense").tooltip(f"Take {name.replace('_', ' ')} away (and its output)")
        ui.button(f"Add {prefix}", icon="add",
                  on_click=lambda: self._set_param(node, count_field(prefix), len(names) + 1, rebuild=True)) \
            .props("no-caps outline dense").classes("self-start")

    async def _change(self, node: NodeDraft) -> None:
        name = await self.picker().pick("Change the action")
        if not name or name == node.action:
            return
        keep = _parameters(self._actions.get(name))
        node.action = name
        node.params = {k: v for k, v in node.params.items() if k in keep}
        self.prepare(node)
        self._on_change(rebuild=True)

    def _wire_by_name(self, node: NodeDraft, action: RegisteredAction) -> None:
        fields = [name for name in _parameters(action) if name != action.data_outputs]

        def apply(chosen: dict[str, str]) -> None:
            node.params.update(chosen)
            self._on_change(rebuild=True)

        WireByNameDialog(fields, self.wire_sources(node), node.params, apply).open()

    def _set_param(self, node: NodeDraft, name: str, value: Any, rebuild: bool = False) -> None:
        action = self.action(node.action)
        if action is not None and name in action.fills:  # e.g. the Raw request's data template
            node.params.update(action.filled(node.params, name, value))
            rebuild = True
        node.params[name] = value
        self._on_change(rebuild=rebuild)

    def _set(self, node: NodeDraft, key: str, value: Any) -> None:
        setattr(node, key, value)
        self._on_change()

    def last_result(self, node_id: str) -> tuple[bool, Any]:
        """(True, what the box gave last time: Test box, Test run or a real run) or (False, None)."""
        return self._runner.last_result(self._draft.name, node_id) if self._draft.name else (False, None)

    @ui.refreshable_method
    def _last_result(self, node: NodeDraft) -> None:
        with ui.expansion("Last result", icon="data_object", value=True).props("dense").classes("w-full text-sm"):
            known, value = self.last_result(node.id)
            if known:
                ResultView.show(value)
            else:
                ui.label("Not run yet: Test box below (or Test run at the top) shows exactly what it gives.") \
                    .classes("text-xs opacity-70")

    async def _test(self, node: NodeDraft, button: ui.button) -> None:
        button.props("loading")
        try:
            result = await self._runner.run_node(self._draft.to_flow(), node.to_node())
        except Exception as e:
            ui.notify(str(e), type="negative", multi_line=True)
        else:
            saved = f" → saved in {node.save_as}" if node.save_as else ""
            ui.notify(f"{self.title(node.action)}: {'done' if result is None else result}{saved}", type="positive",
                      multi_line=True)
            self._last_result.refresh()
        finally:
            button.props(remove="loading")

    async def _capture(self, node: NodeDraft, action: RegisteredAction) -> None:
        """capture "other.action:param": store other.action's result in the variable that param uses;
        capture "other.action": run it with this box's matching parameters."""
        capture, _, param = action.capture.partition(":")
        ui.notify(f"{self.title(capture)} ...", type="ongoing", timeout=2000)  # some wait, e.g. for a click in VTS
        try:
            if param:
                match = VAR.fullmatch(str(node.params.get(param, "")))
                if not match or match.group(2):
                    ui.notify(f"Set {param} to a variable first (Variable, then a name)", type="warning")
                    return
                self._variables.set(match.group(1), await self._actions.run(capture))
                ui.notify(f"Saved in variable {match.group(1)}", type="positive")
            else:
                wanted = _parameters(self._actions.get(capture))
                await self._actions.run(capture, **{k: v for k, v in node.params.items() if k in wanted})
                ui.notify("Saved", type="positive")
        except Exception as e:
            ui.notify(str(e), type="negative", multi_line=True)
        self._on_change(rebuild=True)

    def _capture_tip(self, action: RegisteredAction) -> str:
        capture, _, param = action.capture.partition(":")
        what = self.title(capture)
        return f"Runs {what} now and stores it in the variable of '{param}'" if param else f"Runs {what} now"


# an action's editors kind → the field that edits it
EDITORS = {"vts_animation": AnimationInput, "obs_placement": PlacementInput}


def _with_helpers(ref: str, label: str, kind: str) -> dict[str, str]:
    """A data dot for the field's list, followed by the helpers that fit its kind:
    ${box.n3.@count} → "3 · Get rewards · @count = how many"."""
    return {ref: label} | {ref[:-1] + f".{HELPER}{name}}}": f"{label} · {HELPER}{name} = {HELPERS[name][0]}"
                           for name in helpers_for(kind)}


def _hint(action: RegisteredAction, name: str, node: NodeDraft) -> str:
    """The field's hint: worked out from the box's values (live_hints) or the fixed one."""
    if name in action.live_hints:
        try:
            return action.live_hints[name](node.params)
        except Exception:  # a hint must never break the form
            return action.hints.get(name, "")
    return action.hints.get(name, "")


def _section(title: str) -> None:
    ui.label(title).classes("text-xs font-semibold uppercase tracking-wider text-primary pt-3")


def short_id(node_id: str) -> str:
    """The number a box shows: "3" for n3."""
    return node_id[1:] if node_id[:1] == "n" and node_id[1:].isdigit() else node_id


def _gives_result(action: RegisteredAction) -> bool:
    """False for an action that gives nothing back (-> None) or picks an output (If, For each, Ask yes/no)."""
    if action.ports:
        return False
    returns = inspect.signature(action.handler).return_annotation
    return returns not in (None, "None", type(None)) and "AsyncIterator" not in str(returns)


def _parameters(action: RegisteredAction) -> dict[str, inspect.Parameter]:
    return {p.name: p for p in inspect.signature(action.handler).parameters.values()
            if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)}
