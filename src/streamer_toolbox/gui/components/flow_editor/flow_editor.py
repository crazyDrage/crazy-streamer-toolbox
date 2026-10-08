from collections.abc import Callable
from dataclasses import replace

from nicegui import app, ui

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.box_filter_store import BoxFilterStore
from streamer_toolbox.gui.components.flow_editor.action_picker import SwitchedOff
from streamer_toolbox.core.actions.registered_action import OptionsProvider
from streamer_toolbox.core.data.box_value import understand
from streamer_toolbox.core.files.box_value_files import BoxValueFiles
from streamer_toolbox.core.flows.flow_input import FlowInput
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.chat_match import MODES, WHO, mode_of, to_match
from streamer_toolbox.core.flows.flow_gate import WHEN_BUSY
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.flow_wire import START
from streamer_toolbox.core.variables.variable_store import VariableStore
from streamer_toolbox.gui.components.folder_field import FolderField
from streamer_toolbox.gui.components.flow_editor.flow_box_view import FlowBoxView
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft
from streamer_toolbox.gui.components.flow_editor.flow_list_view import FlowListView
from streamer_toolbox.gui.components.flow_editor.node_editor import NodeEditor
from streamer_toolbox.gui.components.flow_editor.start_examples import StartExamples
from streamer_toolbox.gui.components.flow_editor.trigger_kinds import (TRIGGER_CHOICES, TRIGGER_INFO,
                                                                       TRIGGER_KINDS, offered_triggers)
from streamer_toolbox.gui.components.flow_editor.trigger_picker import TriggerPicker

VIEWS = {"list": "List", "boxes": "Boxes"}


class FlowEditor:
    """One open flow editor (one per browser tab, so tabs don't share a draft): name, description, inputs,
    triggers, and the boxes as a list or as boxes with wires."""

    def __init__(self, draft: FlowDraft, old_name: str | None, library: FlowLibrary, actions: ActionRegistry,
                 runner: FlowRunner, variables: VariableStore, box_files: BoxValueFiles,
                 trigger_choices: dict[str, OptionsProvider] | None = None,
                 box_filters: BoxFilterStore | None = None, switched_off: SwitchedOff | None = None) -> None:
        self._draft = draft
        self._old_name = old_name
        self._library = library
        self._trigger_choices = trigger_choices or {}
        self._switched_off = switched_off
        self._view = app.storage.general.get("flow_view", "list")
        self._runner = runner
        self._nodes = NodeEditor(actions, runner, variables, box_files, draft, self._changed, box_filters,
                                 switched_off)
        self._list = FlowListView(draft, self._nodes)
        self._boxes = FlowBoxView(draft, self._nodes, self._test_run)

    def build(self) -> None:
        FlowBoxView.add_head()
        draft = self._draft
        with ui.row().classes("items-center gap-2 w-full"):
            ui.button(icon="arrow_back").props("flat round href=/flows").tooltip("Back to Flows (unsaved changes "
                                                                                 "are lost)")
            ui.input("Name", value=draft.label, on_change=lambda e: setattr(draft, "label", e.value)) \
                .classes("text-lg flex-1 min-w-[12rem]")
            ui.toggle(VIEWS, value=self._view, on_change=lambda e: self._switch(e.value)).props("no-caps")
            ui.button("Test run", icon="play_circle", on_click=self._test_run).props("no-caps outline") \
                .tooltip("Runs the flow as it is now (not saved yet is fine) and shows on each box what it gave")
            ui.button("Save", icon="save", on_click=self._save).props("no-caps unelevated")
            ui.button("Save as template", icon="bookmark_add", on_click=self._save_template).props("no-caps outline")
        ui.label(f"File: {self._library.folder / (draft.name + '.toml')}" if draft.name
                 else "New flow: the file name comes from the name when you save.").classes("text-xs opacity-60")
        with ui.row().classes("items-start no-wrap gap-4 w-full"):
            ui.textarea("What it does", value=draft.description,
                        on_change=lambda e: setattr(draft, "description", e.value)) \
                .props("autogrow").classes("flex-1 min-w-0")
            FolderField(self._library.folders(), draft.folder,
                        on_change=lambda folder: setattr(draft, "folder", folder)).build() \
                .classes("w-56").tooltip("Where the Flows page lists it: pick one or type a new name")
        with ui.row().classes("items-center gap-4 w-full"):
            ui.select(WHEN_BUSY, value=draft.when_busy, label="Started again while it still runs",
                      on_change=lambda e: setattr(draft, "when_busy", e.value)).classes("w-72") \
                .tooltip("Like SAMMI: Run alongside = overlappable (sounds), Wait in line = queueable (model "
                         "redeems, one after the other), Skip = neither (a second start does nothing)")
            ui.number("Cooldown (s)", value=draft.cooldown or None, min=0,
                      on_change=lambda e: setattr(draft, "cooldown", e.value or 0)).classes("w-32") \
                .tooltip("After a trigger started it, other triggers wait this long (its button doesn't)")
            ui.number("Per viewer (s)", value=draft.user_cooldown or None, min=0,
                      on_change=lambda e: setattr(draft, "user_cooldown", e.value or 0)).classes("w-32") \
                .tooltip("The same viewer has to wait this long before starting it again")
            ui.checkbox("Refund the redeem if it fails", value=draft.refund_on_fail,
                        on_change=lambda e: setattr(draft, "refund_on_fail", e.value)) \
                .tooltip("Also when held back by a cooldown or Skip. Only for rewards the toolbox made "
                         "(Twitch's rule)")
        with ui.row().classes("w-full gap-4 items-start"):
            with ui.expansion(f"Inputs ({len(draft.inputs)})", icon="input").classes("flex-1 min-w-[18rem]") as box:
                self._inputs(box)
            with ui.expansion(f"Triggers ({len(draft.triggers)})", icon="bolt").classes("flex-1 min-w-[18rem]") \
                    as box:
                self._triggers(box)
        self._steps_area()

    @ui.refreshable_method
    def _steps_area(self) -> None:
        if self._view == "boxes":
            self._boxes.build()
        else:
            self._list.build()

    def _changed(self, rebuild: bool = False, edit: Callable[[], None] | None = None) -> None:
        """edit: a change to the graph that renames outputs (taking a Switch case away); the box view makes it
        once it has read back the canvas, which still knows the old names."""
        if self._view == "boxes":
            self._boxes.changed(rebuild, edit)
            return
        if edit is not None:
            edit()
        if rebuild:
            self._list.build.refresh()

    async def _switch(self, view: str) -> None:
        if self._view == "boxes":
            await self._boxes.sync()
        self._view = view
        app.storage.general["flow_view"] = view
        self._steps_area.refresh()

    # ---- inputs and triggers ----

    def _inputs(self, box: ui.expansion) -> None:
        ui.label("Values the flow asks for when it runs, e.g. the video for a soundboard redeem. Each one is an "
                 "orange dot on the Start box (or ${input.name}). Without a default, the Live page asks for it and "
                 "SAMMI must send it.") \
            .classes("text-xs opacity-70")

        @ui.refreshable
        def rows() -> None:
            box.props(f'label="Inputs ({len(self._draft.inputs)})"')
            for index, item in enumerate(self._draft.inputs):
                with ui.row().classes("items-center no-wrap gap-2 w-full"):
                    ui.input("name", value=item.name, on_change=lambda e, i=index: self._set_input(i, name=e.value)) \
                        .props("dense").classes("w-32").on("blur", lambda: self._changed(rebuild=True))
                    ui.input("default", value=item.default or "",
                             on_change=lambda e, i=index: self._set_input(i, default=e.value or None)) \
                        .props("dense").classes("flex-1")
                    ui.button(icon="delete", on_click=lambda i=index: (self._draft.inputs.pop(i), rows.refresh(),
                                                                       self._changed(rebuild=True))) \
                        .props("flat round dense")
            ui.button("Add input", icon="add", on_click=lambda: (
                self._draft.inputs.append(FlowInput(f"value{len(self._draft.inputs) + 1}")), rows.refresh(),
                self._changed(rebuild=True))) \
                .props("no-caps flat dense")

        rows()

    def _set_input(self, index: int, **changes) -> None:
        item = self._draft.inputs[index]
        self._draft.inputs[index] = FlowInput(changes.get("name", item.name).strip(),
                                              changes.get("default", item.default), item.description)


    def _triggers(self, box: ui.expansion) -> None:
        ui.label("Besides its button, the flow also starts when one of these happens. What happened shows as "
                 "orange dots on the Start box: a redeem gives user, reward, input (the text the viewer typed); a "
                 "chat message user, message, args (the text after the command). Wire them into box fields. A chat "
                 "trigger matches a command (!cat, with or without text after it), a text anywhere in the message "
                 "(Contains: lizard), or a Pattern with * like SAMMI.") \
            .classes("text-xs opacity-70")

        @ui.refreshable
        def rows() -> None:
            box.props(f'label="Triggers ({len(self._draft.triggers)})"')
            for index, trigger in enumerate(self._draft.triggers):
                icon, text, key, _ = TRIGGER_KINDS.get(trigger.kind, ("bolt", trigger.kind, "", ""))
                key = key or next(iter(trigger.match), "match")
                # the name on its own line (a long one fits), what it matches below; that line may wrap
                with ui.column().classes("w-full gap-0 pb-2"):
                    with ui.row().classes("items-center no-wrap gap-2 w-full"):
                        ui.icon(icon).classes("text-primary")
                        name = ui.label(text).classes("flex-1 min-w-0 text-sm font-medium")
                        if trigger.kind in TRIGGER_INFO:
                            name.tooltip(TRIGGER_INFO[trigger.kind])
                        ui.button(icon="delete", on_click=lambda i=index: (self._draft.triggers.pop(i),
                                                                           rows.refresh(),
                                                                           self._changed(rebuild=True))) \
                            .props("flat round dense")
                    with ui.row().classes("items-start gap-2 w-full pl-8"):
                        if trigger.kind.rpartition(".")[2] == "chat":  # every platform's chat, and the common one
                            self._chat_match(index, trigger.match)
                        else:
                            self._trigger_value(index, trigger.kind, key, str(trigger.match.get(key, "")))
            ui.button("Add trigger", icon="add", on_click=add).props("no-caps flat dense")

        async def add() -> None:
            picked = await TriggerPicker(offered_triggers(self._switched_off)).pick()
            if picked is None:
                return
            self._draft.triggers.append(FlowTrigger(picked.kind, {picked.match: picked.example}))
            rows.refresh()
            self._changed(rebuild=True)

        rows()

    def _trigger_value(self, index: int, kind: str, key: str, value: str) -> None:
        """The reward (or other match) of a trigger: a list from the service when it has one, typing works too."""
        current = [value] if value else []
        pick = ui.select(current, value=value or None, label=key, new_value_mode="add-unique",
                         on_change=lambda e: self._set_trigger(index, match={key: e.value or ""})) \
            .props("dense").classes("flex-1 min-w-[10rem]")
        provider = self._trigger_choices.get(kind) or TRIGGER_CHOICES.get(kind)
        if provider is None:
            return

        async def load() -> None:
            try:
                choices = await provider()
            except Exception as e:  # not connected: typing still works
                pick.props(f'hint="list not available: {str(e).replace(chr(34), chr(39))}"')
                return
            if isinstance(choices, dict):  # id → name (rewards): the trigger keeps the id, a rename can't break it
                self._by_id(index, key, pick, choices)
                return
            pick.set_options(sorted(set(choices) | set(current), key=str.casefold), value=pick.value)

        ui.timer(0.1, load, once=True)

    def _by_id(self, index: int, key: str, pick: ui.select, choices: dict[str, str]) -> None:
        """A list of names whose items stand for ids (rewards): picking one saves name + id (key_id); a typed name
        or pattern (Lizard*) saves only the name. A saved id shows its name as it is on Twitch now."""
        id_key = f"{key}_id"
        match = self._draft.triggers[index].match
        saved = str(match.get(id_key, ""))
        name = choices.get(saved, str(match.get(key, "")))
        ids = {title: reward_id for reward_id, title in choices.items()}
        pick.set_options(sorted(set(ids) | ({name} if name else set()), key=str.casefold), value=name or None)
        if saved and saved not in choices:
            pick.props(f'hint="this {key} isn\'t on Twitch anymore (deleted?): pick it again"')
        elif saved and name != match.get(key):
            self._set_trigger(index, match={**match, key: name})  # renamed on Twitch: show and save the new name

        def picked(e) -> None:
            text = e.value or ""
            self._set_trigger(index, match={key: text, id_key: ids[text]} if text in ids else {key: text})

        pick.on_value_change(picked)

    def _chat_match(self, index: int, match: dict) -> None:
        """A chat trigger: a command (!cat), a text the message contains (lizard), or a pattern with *."""
        mode, text = mode_of(match)

        def changed() -> None:
            field.props(f'hint="{MODES[how.value][1]}"')
            limit = {} if who.value == "viewer" else {"who": who.value}
            self._set_trigger(index, match={**to_match(how.value, field.value or ""), **limit})

        how = ui.select({m: label for m, (label, _) in MODES.items()}, value=mode, on_change=changed) \
            .props("dense").classes("w-28 shrink-0")
        field = ui.input(value=text, on_change=changed).props(f'dense hint="{MODES[mode][1]}"') \
            .classes("flex-1 min-w-[10rem]")
        who = ui.select(WHO, value=match.get("who", "viewer"), on_change=changed).props("dense") \
            .classes("w-32 shrink-0").tooltip("Who may start it")

    def _set_trigger(self, index: int, **changes) -> None:
        trigger = self._draft.triggers[index]
        self._draft.triggers[index] = FlowTrigger(changes.get("kind", trigger.kind),
                                                  changes.get("match", trigger.match))

    # ---- test run ----

    async def _test_run(self) -> None:
        if self._view == "boxes":
            await self._boxes.sync()
        problem = self._problem()
        if problem:
            ui.notify(problem, type="warning")
            return
        values = {i.name: i.default for i in self._draft.inputs}
        known, last = self._runner.last_result(self._draft.name, START) if self._draft.name else (False, None)
        event = StartExamples.values(self._draft.triggers, last if known and isinstance(last, dict) else None)
        with ui.dialog() as dialog, ui.card().classes("w-[460px] max-w-[95vw]"):
            ui.label("Test run: this runs the flow for real (OBS, SAMMI, sounds, ...).").classes("text-sm")
            for item in self._draft.inputs:  # e.g. the video's path for Play video
                ui.input(item.name, value="" if item.default is None else str(item.default),
                         on_change=lambda e, n=item.name: values.__setitem__(n, e.value)) \
                    .props("dense outlined").classes("w-full")
            if event:
                ui.label("What the trigger gives (the Start box's orange dots)").classes("text-sm font-semibold")
                ui.label(("From the last real start; change them to try other cases." if known else
                          "Examples: change them to what the real trigger would give.")).classes("text-xs opacity-60")
                with ui.element("div").classes("grid grid-cols-2 gap-2 w-full"):
                    for name, value in event.items():
                        ui.input(name, value="" if value is None else str(value),
                                 on_change=lambda e, n=name: event.__setitem__(n, e.value)) \
                            .props("dense outlined").classes("w-full")
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=lambda: dialog.submit(False)).props("flat no-caps")
                ui.button("Run it", icon="play_arrow", on_click=lambda: dialog.submit(True)) \
                    .props("unelevated no-caps")
        if not await dialog:
            return
        inputs = {name: _typed(value) for name, value in values.items() if value not in (None, "")}
        event = {name: _typed(value) for name, value in event.items()}
        results, error = await self._runner.test_run(self._draft.to_flow(), inputs, event)
        failed = getattr(error, "node_id", None)
        if self._view == "boxes":
            self._boxes.show_run(results, failed, str(getattr(error, "cause", error or "")))
        if error is None:
            ui.notify(f"Test run done: {len(results)} boxes ran", type="positive")
        else:
            ui.notify(f"Test run stopped: {error}", type="negative", multi_line=True)

    # ---- saving ----

    async def _save(self) -> None:
        if self._view == "boxes":
            await self._boxes.sync()
        draft = self._draft
        problem = self._problem()
        if problem:
            ui.notify(problem, type="warning")
            return
        if not draft.name:
            draft.name = self._library.free_name(draft.label)
        try:
            self._library.save(draft.to_flow(), self._old_name)
        except Exception as e:
            ui.notify(f"Not saved: {e}", type="negative", multi_line=True)
            return
        ui.notify(f"{draft.label} saved · action flow.{draft.name}", type="positive")
        if self._old_name != draft.name:
            ui.navigate.to(f"/flows/edit?flow={draft.name}")

    async def _save_template(self) -> None:
        if self._view == "boxes":
            await self._boxes.sync()
        problem = self._problem()
        if problem:
            ui.notify(problem, type="warning")
            return
        flow = self._draft.to_flow()
        name = self._library.free_template_name(flow.label)
        self._library.save_template(replace(flow, name=name))
        ui.notify(f"Template {flow.label} saved. New flow → From template uses it.", type="positive")

    def _problem(self) -> str:
        names = [i.name for i in self._draft.inputs]
        if not self._draft.label.strip():
            return "Give the flow a name first"
        if any(not n.isidentifier() for n in names):
            return "Input names: letters, digits and _ only, not starting with a digit"
        if len(set(names)) != len(names):
            return "Two inputs have the same name"
        loop = self._draft.to_flow().data_loop()
        if loop:
            boxes = " → ".join(n[1:] if n[:1] == "n" and n[1:].isdigit() else n for n in loop)
            return f"Boxes {boxes} need each other's value (their orange wires go round): take one of them away"
        return ""


def _typed(value):
    """Test run inputs are typed as text: "3" → 3, "0.5" → 0.5, "true" → True, other text stays text."""
    return understand(value) if isinstance(value, str) else value
