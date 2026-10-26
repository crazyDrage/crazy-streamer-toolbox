import inspect
from collections.abc import Callable
from typing import Any

from nicegui import ui

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.box_filter_store import BoxFilterStore
from streamer_toolbox.core.testing.test_view import TestView
from streamer_toolbox.core.actions.numbered_fields import count_field, numbered_fields
from streamer_toolbox.core.actions.registered_action import RegisteredAction
from streamer_toolbox.core.data.box_value import kind_of
from streamer_toolbox.core.files.box_value_files import BoxValueFiles
from streamer_toolbox.core.flows.box_wire import WIRE_IN, is_wire_in
from streamer_toolbox.core.flows.flow import END_LINE
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.variables.variable_store import VariableStore
from streamer_toolbox.gui.components.flow_editor.action_picker import ActionPicker, SwitchedOff
from streamer_toolbox.gui.components.flow_editor.box_dots import BoxDots, box_parameters
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft
from streamer_toolbox.gui.components.flow_editor.move_buttons import move_buttons
from streamer_toolbox.gui.components.flow_editor.node_draft import NodeDraft
from streamer_toolbox.gui.components.flow_editor.param_input import VAR, ParamInput
from streamer_toolbox.gui.components.flow_editor.result_view import ResultView
from streamer_toolbox.gui.components.flow_editor.value_lines_input import LINE_NAME, ValueLinesInput
from streamer_toolbox.gui.components.flow_editor.value_editors import EDITORS
from streamer_toolbox.gui.components.keep_typed import keep_typed


class NodeEditor:
    """The form for one box: its action (Change opens the Add menu), each parameter (value, variable, Live value,
    flow input or a wire from another box), "save result in variable", on/off, note, and the Test and Save current
    buttons. What a box takes and gives (its fields, data dots and kinds) is in `dots` (BoxDots).

    on_change() after an edit; on_change(rebuild=True) when the box's outputs or form changed shape."""

    def __init__(self, actions: ActionRegistry, runner: FlowRunner, variables: VariableStore,
                 box_files: BoxValueFiles, draft: FlowDraft, on_change: Callable[..., None],
                 box_filters: BoxFilterStore | None = None, switched_off: SwitchedOff | None = None,
                 test_view: TestView | None = None) -> None:
        self._actions = actions
        self._runner = runner
        self._variables = variables
        self._box_files = box_files
        self._draft = draft
        self._on_change = on_change
        self._box_filters = box_filters
        self._switched_off = switched_off
        self._test_view = test_view
        self.dots = BoxDots(actions, runner, draft)

    def picker(self) -> ActionPicker:
        return ActionPicker(self._actions, f"flow.{self._draft.name}" if self._draft.name else "",
                            self._box_filters, self._switched_off, self._test_view)

    def prepare(self, node: NodeDraft) -> None:
        """A new box: a Switch and Choose value with two cases / lines; a Value box with one line."""
        action = self.dots.action(node.action)
        if action and action.value_lines:
            node.params.setdefault(action.value_lines, {"value": ""})
        if action and action.port_fields:
            node.params.setdefault(count_field(action.port_fields), 2)
        if action and action.entry_fields:
            node.params.setdefault(count_field(action.entry_fields), 2)

    async def _variable_names(self) -> list[str]:
        return self._variables.names()

    def build(self, node: NodeDraft) -> None:
        action = self.dots.action(node.action)
        with ui.row().classes("items-center no-wrap gap-2 w-full"):
            with ui.column().classes("gap-0 flex-1 min-w-0"):
                ui.label(self.dots.title(node.action)).classes("font-medium")
                ui.label(action.description if action else "Unknown action: its connection or plugin isn't "
                         "loaded").classes("text-xs " + ("opacity-70" if action else "text-negative"))
            ui.button("Change", icon="swap_horiz", on_click=lambda: self._change(node)).props("no-caps flat dense")
        parameters = box_parameters(action) if action is not None else {}
        if parameters or (action is not None and action.named_lines):  # End has no fields of its own, only lines
            _section("Settings")
            live = {a.name: f"{a.category_title} · {a.title}" for a in self._actions.live()}
            sources = self.dots.wire_sources(node)
            warnings = self.dots.wire_warnings(node)
            shown = {n: p for n, p in parameters.items()
                     if action.shows(n, node.params) and n != action.entry_fields}  # lines: _numbered
            choosers = action.choosers()
            for index, (name, parameter) in enumerate(shown.items()):
                if index:
                    ui.separator().classes("opacity-40")
                if name == action.value_lines:
                    lines = node.params.get(name)
                    ValueLinesInput(lines if isinstance(lines, dict) else {},
                                    lambda value, moved, n=name: self._set_lines(node, n, value, moved),
                                    _hint(action, name, node), self._variables).build()
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
                options = action.options.get(name) or (self._variable_names if name in action.variable_fields
                                                        else None)  # a field with a variable's name: pick one
                ParamInput(name, default, value, parameter.annotation, options,
                           self._variables, [i.name for i in self._draft.inputs], live, self._actions.run, sources,
                           lambda value, rebuild, n=name: self._set_param(node, n, value, rebuild or n in choosers),
                           warnings.get(name, ""), action.labels.get(name, ""), _hint(action, name, node),
                           action.files.get(name), name in action.colors, action.many.get(name),
                           action.lights.get(name)).build()
            for prefix in (action.port_fields, action.entry_fields):
                if prefix:
                    self._numbered(node, action, prefix, live, sources, warnings)
            if action.named_lines:
                self._named_lines(node, action, live, sources, warnings)
        _section("Result")
        names = sorted(set(self._variables.names()) | ({node.save_as} if node.save_as else set()), key=str.casefold)
        keep_typed(ui.select(names, value=node.save_as or None, label="save it in a variable (optional)",
                             new_value_mode="add-unique", clearable=True,
                             on_change=lambda e: self._set(node, "save_as", e.value or ""))
                   .props("outlined dense options-dense").classes("w-full"))
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
            if action and action.capture and action.shows(action.capture.partition(":")[2], node.params):
                ui.button("Save current", icon="my_location", on_click=lambda: self._capture(node, action)) \
                    .props("no-caps outline dense").tooltip(self._capture_tip(action))

    def _numbered(self, node: NodeDraft, action: RegisteredAction, prefix: str, live: dict[str, str],
                  sources: dict[str, str], warnings: dict[str, str]) -> None:
        """A Switch's cases or a box's lines (Choose value, End): one field each (with x to take it and its output
        or run dot away) and "+ Add case"."""
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
                    move_buttons(number, len(names), lambda step, n=number: self._on_change(
                        rebuild=True, edit=lambda: self._draft.move_numbered(node.id, prefix, n, step)))
                    ui.button(icon="close", on_click=lambda n=number: self._on_change(
                        rebuild=True, edit=lambda: self._draft.remove_numbered(node.id, prefix, n))) \
                        .props("flat round dense").tooltip(f"Take {name.replace('_', ' ')} away (and its dot)")
        ui.button(f"Add {prefix}", icon="add",
                  on_click=lambda: self._set_param(node, count_field(prefix), len(names) + 1, rebuild=True)) \
            .props("no-caps outline dense").classes("self-start")

    def _named_lines(self, node: NodeDraft, action: RegisteredAction, live: dict[str, str], sources: dict[str, str],
                     warnings: dict[str, str]) -> None:
        """End's values: a name and a value each (typed or a wire), x to take one away and "+ Add value". Every line
        is an orange dot on the box; in another flow it is a dot of this flow's box, named like the line."""
        ui.separator().classes("opacity-40")
        ui.label("Values it gives back").classes("text-sm font-semibold")
        lines = action.lines_named(node.params)
        for number, name in enumerate(lines, 1):
            ui.separator().classes("opacity-40")
            with ui.row().classes("items-center no-wrap w-full gap-1"):
                ui.input("name", value=name).props("outlined dense").classes("flex-1 min-w-0") \
                    .on("blur", lambda e, n=name: self._rename_line(node, n, e.sender.value))
                if len(lines) > 1:
                    move_buttons(number, len(lines), lambda step, n=name: self._on_change(
                        rebuild=True, edit=lambda: _move_key(node.params, n, step, lines)))
                ui.button(icon="close", on_click=lambda n=name: self._on_change(
                    rebuild=True, edit=lambda: node.params.pop(n, None))) \
                    .props("flat round dense").tooltip("Take this value away (and its dot)")
            ParamInput(name, None, node.params.get(name, ""), Any, None, self._variables,
                       [i.name for i in self._draft.inputs], live, self._actions.run, sources,
                       lambda value, rebuild, n=name: self._set_param(node, n, value, rebuild),
                       warnings.get(name, ""), label="value").build()
        ui.button("Add value", icon="add", on_click=lambda: self._add_line(node, action)) \
            .props("no-caps outline dense").classes("self-start")

    def _add_line(self, node: NodeDraft, action: RegisteredAction) -> None:
        number = len(action.lines_named(node.params)) + 1
        while f"value_{number}" in node.params:
            number += 1
        node.params[f"value_{number}"] = WIRE_IN  # most come from a box; "Value" in its field to type one
        self._on_change(rebuild=True)

    def _rename_line(self, node: NodeDraft, old: str, new: str) -> None:
        """A line's new name; its value (and wire) goes along. The canvas is read back first (see _set_param)."""
        new = (new or "").strip().replace(" ", "_")
        if new == old:
            return
        if not LINE_NAME.fullmatch(new) or new == END_LINE:
            ui.notify(f"A name takes letters, digits and _ only (and isn't {END_LINE})", type="warning")
        elif new in node.params:
            ui.notify(f"There is a value named {new} already", type="warning")
        else:
            self._on_change(rebuild=True, edit=lambda: _rename_key(node.params, old, new))
            return
        self._on_change(rebuild=True)  # the form shows the old name again

    async def _change(self, node: NodeDraft) -> None:
        name = await self.picker().pick("Change the action")
        if not name or name == node.action:
            return
        keep = box_parameters(self._actions.get(name))
        node.action = name
        node.params = {k: v for k, v in node.params.items() if k in keep}
        self.prepare(node)
        self._on_change(rebuild=True)

    def _set_param(self, node: NodeDraft, name: str, value: Any, rebuild: bool = False) -> None:
        action = self.dots.action(node.action)
        if action is not None and name in action.fills:  # e.g. the Raw request's data template
            node.params.update(action.filled(node.params, name, value))
            rebuild = True
        if is_wire_in(value) and is_wire_in(node.params.get(name)):
            # a wire picked or taken away (the X) in the panel: the canvas still shows the old wire and would put
            # it back when it is read, so the change is made after that
            self._on_change(rebuild=True, edit=lambda: node.params.__setitem__(name, value))
            return
        node.params[name] = value
        self._on_change(rebuild=rebuild)

    def _set_lines(self, node: NodeDraft, name: str, lines: dict[str, Any], moved: tuple[str, str] | None) -> None:
        """A Value box's lines. When its dots changed, the canvas is read back first (by the dot names it was drawn
        with), then the lines are set and the wires of a renamed or removed line follow (see _set_param)."""
        if moved is None:
            node.params[name] = lines
            self._on_change()
            return

        def edit() -> None:
            node.params[name] = lines
            if moved[0]:
                self._draft.rename_output(node.id, *moved)

        self._on_change(rebuild=True, edit=edit)

    def _set(self, node: NodeDraft, key: str, value: Any) -> None:
        setattr(node, key, value)
        self._on_change()

    @ui.refreshable_method
    def _last_result(self, node: NodeDraft) -> None:
        with ui.expansion("Last result", icon="data_object", value=True).props("dense").classes("w-full text-sm"):
            known, value = self.dots.last_result(node.id)
            if known:
                ResultView.show(value)
                action = self.dots.action(node.action)
                if action and isinstance(value, dict) and not (action.value_lines or action.keys_of):
                    with ui.row().classes("gap-1"):
                        ui.button("Dots from this result", icon="scatter_plot",
                                  on_click=lambda: self._own_outputs(node, value)) \
                            .props("no-caps outline dense") \
                            .tooltip("An orange dot per key of this result, on this box only (kept in the flow)")
                        if node.outputs:
                            ui.button("No own dots", icon="remove_circle_outline",
                                      on_click=lambda: self._own_outputs(node, {})).props("no-caps flat dense")
            else:
                ui.label("Not run yet: Test box below (or Test run at the top) shows exactly what it gives.") \
                    .classes("text-xs opacity-70")

    def _own_outputs(self, node: NodeDraft, result: dict[str, Any]) -> None:
        """Dots from this result: the box's own data dots are the result's keys (his round 60: on this one box in
        this flow, instead of a new box)."""
        node.outputs = {str(k): kind_of(v) for k, v in result.items()}
        self._on_change(rebuild=True)
        self._last_result.refresh()

    async def _test(self, node: NodeDraft, button: ui.button) -> None:
        button.props("loading")
        try:
            result = await self._runner.run_node(self._draft.to_flow(), node.to_node())
        except Exception as e:
            ui.notify(str(e), type="negative", multi_line=True)
        else:
            saved = f" → saved in {node.save_as}" if node.save_as else ""
            ui.notify(f"{self.dots.title(node.action)}: {'done' if result is None else result}{saved}", type="positive",
                      multi_line=True)
            self._last_result.refresh()
        finally:
            button.props(remove="loading")

    async def _capture(self, node: NodeDraft, action: RegisteredAction) -> None:
        """capture "other.action:param": store other.action's result in the variable that param uses;
        capture "other.action": run it with this box's matching parameters."""
        capture, _, param = action.capture.partition(":")
        ui.notify(f"{self.dots.title(capture)} ...", type="ongoing", timeout=2000)  # some wait, e.g. for a click in VTS
        try:
            if param:
                match = VAR.fullmatch(str(node.params.get(param, "")))
                if not match or match.group(2):
                    ui.notify(f"Set {param} to a variable first (Variable, then a name)", type="warning")
                    return
                self._variables.set(match.group(1), await self._actions.run(capture))
                ui.notify(f"Saved in variable {match.group(1)}", type="positive")
            else:
                wanted = box_parameters(self._actions.get(capture))
                await self._actions.run(capture, **{k: v for k, v in node.params.items() if k in wanted})
                ui.notify("Saved", type="positive")
        except Exception as e:
            ui.notify(str(e), type="negative", multi_line=True)
        self._on_change(rebuild=True)

    def _capture_tip(self, action: RegisteredAction) -> str:
        capture, _, param = action.capture.partition(":")
        what = self.dots.title(capture)
        return f"Runs {what} now and stores it in the variable of '{param}'" if param else f"Runs {what} now"


# an action's editors kind → the field that edits it


def _hint(action: RegisteredAction, name: str, node: NodeDraft) -> str:
    """The field's hint: worked out from the box's values (live_hints) or the fixed one."""
    if name in action.live_hints:
        try:
            return action.live_hints[name](node.params)
        except Exception:  # a hint must never break the form
            return action.hints.get(name, "")
    return action.hints.get(name, "")


def _rename_key(params: dict[str, Any], old: str, new: str) -> None:
    """Renames a key in place, keeping the order (a line stays where it was)."""
    items = [(new if k == old else k, v) for k, v in params.items()]
    params.clear()
    params.update(items)


def _move_key(params: dict[str, Any], name: str, step: int, among: list[str]) -> None:
    """Moves one of the lines (among) up (step -1) or down (+1) by trading places with its neighbour; the other
    keys stay where they are."""
    index = among.index(name)
    if not 0 <= index + step < len(among):
        return
    other = among[index + step]
    items = [(other if k == name else name if k == other else k, params[other] if k == name else
              params[name] if k == other else v) for k, v in params.items()]
    params.clear()
    params.update(items)


def _section(title: str) -> None:
    ui.label(title).classes("text-xs font-semibold uppercase tracking-wider text-primary pt-3")
