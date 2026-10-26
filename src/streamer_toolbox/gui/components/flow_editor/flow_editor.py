from collections.abc import Callable
from dataclasses import replace

from nicegui import app, ui

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.box_filter_store import BoxFilterStore
from streamer_toolbox.gui.components.flow_editor.action_picker import SwitchedOff
from streamer_toolbox.core.actions.registered_action import OptionsProvider
from streamer_toolbox.core.data.box_value import understand
from streamer_toolbox.core.events.last_events import LastEvents
from streamer_toolbox.core.files.box_value_files import BoxValueFiles
from streamer_toolbox.core.flows.flow_input import FlowInput
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.events.event_fields import EVENT_FIELDS
from streamer_toolbox.core.flows.chat_match import MODES, mode_of, to_match
from streamer_toolbox.core.flows.number_match import COMPARE, CROSSING, compare_of, to_compare
from streamer_toolbox.core.flows.role_match import ROLE_KEYS, roles_match, roles_of
from streamer_toolbox.gui.components.keep_typed import keep_typed
from streamer_toolbox.gui.components.role_picker import RolePicker
from streamer_toolbox.core.flows.flow_gate import WHEN_BUSY
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.flow_wire import INPUT, START
from streamer_toolbox.core.testing.test_view import TestView
from streamer_toolbox.core.variables.variable_store import VariableStore
from streamer_toolbox.gui.components.folder_field import FolderField
from streamer_toolbox.gui.components.flow_editor.flow_box_view import FlowBoxView
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft
from streamer_toolbox.gui.components.flow_editor.flow_list_view import FlowListView
from streamer_toolbox.gui.components.flow_editor.key_dialog import KeyDialog
from streamer_toolbox.gui.components.flow_editor.node_editor import NodeEditor
from streamer_toolbox.gui.components.flow_editor.start_examples import StartExamples
from streamer_toolbox.gui.components.flow_editor.trigger_kinds import (NUMBER_TRIGGERS, TRIGGER_CHOICES, TRIGGER_INFO,
                                                                       TRIGGER_KINDS, offered_triggers)
from streamer_toolbox.gui.components.flow_editor.trigger_picker import TriggerPicker

VIEWS = {"list": "List", "boxes": "Boxes"}
KEY = "key.pressed"  # its key is picked in a window (KeyDialog)


REDEEM = "twitch.redeem"  # its form has the refund checkbox


class FlowEditor:
    """One open flow editor (one per browser tab, so tabs don't share a draft): name, description, inputs,
    triggers, and the boxes as a list or as boxes with wires. In the box view each trigger is a Start box and the
    inputs are the Input box (his round 63): they are set in its panel; the list view has them on top."""

    def __init__(self, draft: FlowDraft, old_name: str | None, library: FlowLibrary, actions: ActionRegistry,
                 runner: FlowRunner, variables: VariableStore, box_files: BoxValueFiles,
                 trigger_choices: dict[str, OptionsProvider] | None = None,
                 box_filters: BoxFilterStore | None = None, switched_off: SwitchedOff | None = None,
                 last_events: LastEvents | None = None, test_view: TestView | None = None) -> None:
        self._last_events = last_events
        self._test_view = test_view
        self._draft = draft
        self._old_name = old_name
        self._library = library
        self._trigger_choices = trigger_choices or {}
        self._switched_off = switched_off
        self._view = app.storage.general.get("flow_view", "list")
        self._runner = runner
        self._running = False  # a run of this flow goes on (the Stop button shows)
        self._nodes = NodeEditor(actions, runner, variables, box_files, draft, self._changed, box_filters,
                                 switched_off, test_view)
        # a box that only gives values has no run wire, also in a flow saved before it was one (shoutout_clip)
        for node in draft.nodes:
            if self._nodes.dots.data_only(node):
                draft.take_off_run_wires(node.id)
        self._list = FlowListView(draft, self._nodes)
        self._boxes = FlowBoxView(draft, self._nodes, self._test_run, self._test_from, self._start_form,
                                  self._add_trigger)

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
            stop = ui.button("Stop", icon="stop", on_click=self._stop).props("no-caps unelevated color=negative") \
                .tooltip("Stops this flow where it is: its Test runs and its real runs (a loop too)")
            stop.bind_visibility_from(self, "_running")
            ui.timer(1.0, lambda: setattr(self, "_running", self._runner.running(self._draft.name) > 0))
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
            ui.switch("Flow on", value=draft.enabled, on_change=lambda e: setattr(draft, "enabled", e.value)) \
                .tooltip("Off: the flow doesn't start at all: not by its button, SAMMI, the API, another flow or "
                         "a trigger. Test run here still works. Saved with the flow")
            ui.switch("Triggers on", value=draft.triggers_enabled,
                      on_change=lambda e: setattr(draft, "triggers_enabled", e.value)) \
                .tooltip("Off: its triggers don't start it; its button and everything else still do. Saved "
                         "with the flow")
            ui.switch("Offered as a box", value=draft.as_box, on_change=lambda e: setattr(draft, "as_box", e.value)) \
                .tooltip("Off: Add box in other flows doesn't list it. Flows that use it already keep their box. "
                         "Saved with the flow")
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
        self._steps_area()

    @ui.refreshable_method
    def _steps_area(self) -> None:
        if self._view == "boxes":
            self._boxes.build()
            return
        draft = self._draft
        with ui.row().classes("w-full gap-4 items-start"):
            with ui.expansion(f"Inputs ({len(draft.inputs)})", icon="input").classes("flex-1 min-w-[18rem]") as box:
                self._inputs(box)
            with ui.expansion(f"Triggers ({len(draft.triggers)})", icon="bolt").classes("flex-1 min-w-[18rem]") \
                    as box:
                self._triggers(box)
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

    def _start_form(self, box: str) -> None:
        """What is set on a Start box or the Input box, in its panel on the canvas."""
        if box == INPUT:
            self._inputs(None)
        elif self._draft.trigger(box) is not None:
            self._trigger_form(box)

    def _inputs(self, box: ui.expansion | None) -> None:
        """The inputs: on top of the list view (box = its expansion) or in the Input box's panel."""
        ui.label("Values the flow asks for when it runs, e.g. the video for a soundboard redeem. Each one is an "
                 "orange dot on the Input box (or ${input.name}). Without a default, the Live page asks for it and "
                 "SAMMI must send it.") \
            .classes("text-xs opacity-70")

        @ui.refreshable
        def rows() -> None:
            if box is not None:
                box.props(f'label="Inputs ({len(self._draft.inputs)})"')
            for index, item in enumerate(self._draft.inputs):
                with ui.row().classes("items-center no-wrap gap-2 w-full"):
                    ui.input("name", value=item.name, on_change=lambda e, i=index: self._set_input(i, name=e.value)) \
                        .props("dense").classes("w-32").on("blur", lambda: self._changed(rebuild=True))
                    ui.input("default", value=item.default or "",
                             on_change=lambda e, i=index: self._set_input(i, default=e.value or None)) \
                        .props("dense").classes("flex-1")
                    ui.button(icon="delete", on_click=lambda i=index: self._changed(
                        edit=lambda: (self._draft.inputs.pop(i), rows.refresh()))) \
                        .props("flat round dense")
            ui.button("Add input", icon="add", on_click=lambda: self._changed(edit=lambda: (
                self._draft.inputs.append(FlowInput(f"value{len(self._draft.inputs) + 1}")), rows.refresh()))) \
                .props("no-caps flat dense")

        rows()

    def _set_input(self, index: int, **changes) -> None:
        item = self._draft.inputs[index]
        self._draft.inputs[index] = FlowInput(changes.get("name", item.name).strip(),
                                              changes.get("default", item.default), item.description)

    def _triggers(self, box: ui.expansion) -> None:
        """The triggers on top of the list view; the box view shows each as its Start box."""
        ui.label("Besides its button, the flow also starts when one of these happens. Each one is a Start box of "
                 "its own (Boxes view): its orange dots give what happened: a redeem gives user, reward, input (the "
                 "text the viewer typed); a chat message user, message, args (the text after the command). A chat "
                 "trigger matches a command (!cat, with or without text after it), a text anywhere in the message "
                 "(Contains: lizard), or a Pattern with * like SAMMI.") \
            .classes("text-xs opacity-70")

        @ui.refreshable
        def rows() -> None:
            box.props(f'label="Triggers ({len(self._draft.triggers)})"')
            for trigger in self._draft.triggers:
                with ui.column().classes("w-full gap-0 pb-2"):
                    self._trigger_form(trigger.id, lambda i=trigger.id: self._changed(
                        edit=lambda: (self._draft.remove_trigger(i), rows.refresh())))
            ui.button("Add trigger", icon="add", on_click=lambda: self._add_trigger(rows.refresh)) \
                .props("no-caps flat dense")

        rows()

    async def _add_trigger(self, then: Callable[[], None] = lambda: None) -> None:
        """The Add trigger window; the one picked gets its Start box, wired like the Manual Start."""
        kinds = offered_triggers(self._switched_off, self._test_view)
        hidden = len(offered_triggers(self._switched_off)) - len(kinds)
        note = (f"{hidden} triggers hidden: {self._test_view.why()}. Change it in Settings → What "
                "you see") if hidden else ""
        picked = await TriggerPicker(kinds, note).pick()
        if picked is None:
            return
        trigger = FlowTrigger(picked.kind, {picked.match: picked.example} if picked.match else {})
        self._changed(edit=lambda: (self._draft.add_trigger(trigger), then()))

    def _trigger_form(self, trigger_id: str, delete: Callable[[], None] | None = None) -> None:
        """One trigger: its name (with a delete button in the list view) and what it matches."""
        trigger = self._draft.trigger(trigger_id)
        icon, text, key, _ = TRIGGER_KINDS.get(trigger.kind, ("bolt", trigger.kind, None, ""))
        if key is None:  # a kind this copy doesn't know: show what its file says
            key = next(iter(trigger.match), "match")
        elif not key and set(trigger.match) - set(ROLE_KEYS):  # e.g. an older Stream offline's "type"
            self._set_trigger(trigger_id, match=self._who(trigger_id))
        # the name on its own line (a long one fits), what it matches below; that line may wrap
        with ui.row().classes("items-center no-wrap gap-2 w-full"):
            ui.icon(icon).classes("text-primary")
            name = ui.label(text).classes("flex-1 min-w-0 text-sm font-medium")
            if trigger.kind in TRIGGER_INFO:
                name.tooltip(TRIGGER_INFO[trigger.kind])
            if delete is not None:
                ui.button(icon="delete", on_click=delete).props("flat round dense")
        with ui.row().classes("items-start gap-2 w-full" + (" pl-8" if delete is not None else "")):
            if trigger.kind.rpartition(".")[2] == "chat":  # every platform's chat, and the common one
                self._chat_match(trigger_id, trigger.match)
            elif trigger.kind in NUMBER_TRIGGERS:
                self._number_match(trigger_id, key, str(trigger.match.get(key, "*")))
            elif trigger.kind == KEY:
                self._key_match(trigger_id, str(trigger.match.get(key, "")))
            elif not key:  # nothing to pick on it (Stream offline)
                ui.label("Starts every time; it has nothing to filter by.").classes("text-xs opacity-60")
            else:
                self._trigger_value(trigger_id, trigger.kind, key, str(trigger.match.get(key, "")))
                if "role" in EVENT_FIELDS.get(trigger.kind, ()):
                    self._who_select(trigger_id)
        if trigger.kind == REDEEM:  # with the reward it is about (his round 63; one setting for the flow)
            ui.checkbox("Refund the redeem if it fails", value=self._draft.refund_on_fail,
                        on_change=lambda e: setattr(self._draft, "refund_on_fail", e.value)) \
                .classes("text-sm" + (" pl-8" if delete is not None else "")) \
                .tooltip("Also when held back by a cooldown or Skip. Only for rewards the toolbox made "
                         "(Twitch's rule). Counts for every redeem trigger of this flow")

    def _trigger_value(self, trigger_id: str, kind: str, key: str, value: str) -> None:
        """The reward (or other match) of a trigger: a list from the service when it has one, typing works too.
        Without a list it is a plain text field, saved as it is typed (a list's typed value needs Enter)."""
        def changed(e) -> None:
            self._set_trigger(trigger_id, match={key: e.value or "", **self._who(trigger_id)})

        provider = self._trigger_choices.get(kind) or TRIGGER_CHOICES.get(kind)
        if provider is None:
            ui.input(label=key, value=value, on_change=changed).props("dense").classes("flex-1 min-w-[10rem]")
            return
        current = [value] if value else []
        pick = ui.select(current, value=value or None, label=key, new_value_mode="add-unique",
                         on_change=changed).props("dense").classes("flex-1 min-w-[10rem]")
        keep_typed(pick)

        async def load() -> None:
            try:
                choices = await provider()
            except Exception as e:  # not connected: typing still works
                pick.props(f'hint="list not available: {str(e).replace(chr(34), chr(39))}"')
                return
            if isinstance(choices, dict):  # id → name (rewards): the trigger keeps the id, a rename can't break it
                self._by_id(trigger_id, key, pick, choices)
                return
            pick.set_options(sorted(set(choices) | set(current), key=str.casefold), value=pick.value)

        ui.timer(0.1, load, once=True)

    def _by_id(self, trigger_id: str, key: str, pick: ui.select, choices: dict[str, str]) -> None:
        """A list of names whose items stand for ids (rewards): picking one saves name + id (key_id); a typed name
        or pattern (Lizard*) saves only the name. A saved id shows its name as it is on Twitch now."""
        id_key = f"{key}_id"
        match = self._draft.trigger(trigger_id).match
        saved = str(match.get(id_key, ""))
        name = choices.get(saved, str(match.get(key, "")))
        ids = {title: reward_id for reward_id, title in choices.items()}
        pick.set_options(sorted(set(ids) | ({name} if name else set()), key=str.casefold), value=name or None)
        if saved and saved not in choices:
            pick.props(f'hint="this {key} isn\'t on Twitch anymore (deleted?): pick it again"')
        elif saved and name != match.get(key):
            self._set_trigger(trigger_id, match={**match, key: name})  # renamed on Twitch: show and save it

        def picked(e) -> None:
            text = e.value or ""
            found = {key: text, id_key: ids[text]} if text in ids else {key: text}
            self._set_trigger(trigger_id, match={**found, **self._who(trigger_id)})

        pick.on_value_change(picked)

    def _number_match(self, trigger_id: str, key: str, saved: str) -> None:
        """A trigger on a number (Heart rate changed): any, or higher than / lower than / equal to / rises above /
        falls below a number."""
        how, number = compare_of(saved) or ("", 100.0)

        def changed() -> None:
            amount.set_visibility(bool(pick.value))
            self._set_trigger(trigger_id, match={key: to_compare(pick.value, amount.value), **self._who(trigger_id)})

        def hint() -> str:
            if pick.value in CROSSING:
                return "Starts once, when it crosses the number."
            return "Starts at every change that fits; give the flow a cooldown if that is too often."

        pick = ui.select(COMPARE, value=how, label=key, on_change=changed).props("dense").classes("w-36 shrink-0")
        amount = ui.number(value=number, on_change=changed).props("dense").classes("w-24 shrink-0")
        amount.set_visibility(bool(how))
        ui.label().bind_text_from(pick, "value", backward=lambda _: hint()) \
            .classes("text-xs opacity-60 self-center")

    def _key_match(self, trigger_id: str, value: str) -> None:
        """A Key trigger: the key's name, typed or picked in a window (KeyDialog)."""
        field = ui.input(label="key", value=value,
                         on_change=lambda e: self._set_trigger(trigger_id,
                                                               match={"key": (e.value or "").strip().lower()})) \
            .props("dense").classes("flex-1 min-w-[10rem]")

        async def choose() -> None:
            picked = await KeyDialog(field.value or "").pick()
            if picked:
                field.set_value(picked)

        ui.button("Choose key", icon="keyboard", on_click=choose).props("no-caps outline dense") \
            .tooltip("Tick Ctrl / Alt / Shift and pick the key from a list, or press it")

    def _who(self, trigger_id: str) -> dict[str, str]:
        """The trigger's role filter as it is saved (kept when its other field changes)."""
        return {k: v for k, v in self._draft.trigger(trigger_id).match.items() if k in ROLE_KEYS}

    def _who_select(self, trigger_id: str, chat: bool = False) -> None:
        """Who may start it: a checkbox per role (RolePicker), on a trigger that names a viewer. Only chat tells
        a role: the others go by what the toolbox knows of the viewer (Settings → Viewer roles)."""
        def changed(roles: list[str]) -> None:
            match = self._draft.trigger(trigger_id).match
            self._set_trigger(trigger_id, match={**{k: v for k, v in match.items() if k not in ROLE_KEYS},
                                                 **roles_match(roles)})

        RolePicker(roles_of(self._draft.trigger(trigger_id).match), changed,
                   "" if chat else "This trigger doesn't tell the role itself: it is the one the toolbox knows of "
                                   "the viewer (Settings → Viewer roles); unknown counts as a plain viewer.")

    def _chat_match(self, trigger_id: str, match: dict) -> None:
        """A chat trigger: a command (!cat), a text the message contains (lizard), or a pattern with *."""
        mode, text = mode_of(match)

        def changed() -> None:
            field.props(f'hint="{MODES[how.value][1]}"')
            self._set_trigger(trigger_id, match={**to_match(how.value, field.value or ""), **self._who(trigger_id)})

        how = ui.select({m: label for m, (label, _) in MODES.items()}, value=mode, on_change=changed) \
            .props("dense").classes("w-28 shrink-0")
        field = ui.input(value=text, on_change=changed).props(f'dense hint="{MODES[mode][1]}"') \
            .classes("flex-1 min-w-[10rem]")
        self._who_select(trigger_id, chat=True)

    def _set_trigger(self, trigger_id: str, **changes) -> None:
        self._draft.set_trigger(trigger_id, **changes)
        if self._view == "boxes":
            self._boxes.start_changed(trigger_id)  # its line under the title (the reward, the command)

    # ---- test run ----

    async def _test_run(self, start: str | None = None) -> None:
        """Test run from a Start box (start: its id; None = choose in the window when there are triggers)."""
        if self._view == "boxes":
            await self._boxes.sync()
        problem = self._problem()
        if problem:
            ui.notify(problem, type="warning")
            return
        values = {i.name: i.default for i in self._draft.inputs}
        chosen = {"start": start or (self._draft.triggers[0].id if self._draft.triggers else START)}
        event: dict = {}
        with ui.dialog() as dialog, ui.card().classes("w-[460px] max-w-[95vw]"):
            ui.label("Test run: this runs the flow for real (OBS, SAMMI, sounds, ...).").classes("text-sm")
            if start is None and self._draft.triggers:
                ui.select({box: self._nodes.dots.start_text(box)[0] for box in self._nodes.dots.start_boxes()[:-1]},
                          value=chosen["start"], label="Start at",
                          on_change=lambda e: (chosen.__setitem__("start", e.value), given.refresh())) \
                    .props("dense outlined").classes("w-full")
            for item in self._draft.inputs:  # e.g. the video's path for Play video
                ui.input(item.name, value="" if item.default is None else str(item.default),
                         on_change=lambda e, n=item.name: values.__setitem__(n, e.value)) \
                    .props("dense outlined").classes("w-full")

            @ui.refreshable
            def given() -> None:
                event.clear()
                known, last = self._last_start(chosen["start"])
                trigger = self._draft.trigger(chosen["start"])
                event.update(StartExamples.values([trigger] if trigger else [], last if known else None))
                if not event:
                    return
                ui.label("What the trigger gives (its Start box's orange dots)").classes("text-sm font-semibold")
                ui.label(("From the last real start; change them to try other cases." if known else
                          "Examples: change them to what the real trigger would give.")).classes("text-xs opacity-60")
                with ui.element("div").classes("grid grid-cols-2 gap-2 w-full"):
                    for name, value in event.items():
                        ui.input(name, value="" if value is None else str(value),
                                 on_change=lambda e, n=name: event.__setitem__(n, e.value)) \
                            .props("dense outlined").classes("w-full")

            given()
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=lambda: dialog.submit(False)).props("flat no-caps")
                ui.button("Run it", icon="play_arrow", on_click=lambda: dialog.submit(True)) \
                    .props("unelevated no-caps")
        if not await dialog:
            return
        inputs = {name: _typed(value) for name, value in values.items() if value not in (None, "")}
        typed = {name: _typed(value) for name, value in event.items()}
        self._show_test(*await self._runner.test_run(self._draft.to_flow(), inputs, typed, start=chosen["start"]))

    def _stop(self) -> None:
        stopped = self._runner.stop(self._draft.name)
        ui.notify(f"Stopped {stopped} run{'s' if stopped != 1 else ''}" if stopped else "Nothing was running",
                  type="positive" if stopped else "info")
        self._running = False

    def _last_start(self, start: str) -> tuple[bool, dict | None]:
        """What a Start box gave last time: its own last start, else what its trigger's event gave last."""
        known, last = self._runner.last_result(self._draft.name, start) if self._draft.name else (False, None)
        trigger = self._draft.trigger(start)
        if not known and trigger is not None and self._last_events is not None:
            last = self._last_events.get(trigger.kind)
            known = last is not None
        return (True, last) if known and isinstance(last, dict) else (False, None)

    async def _test_from(self, node_id: str) -> None:
        """Test run from one box on (the canvas's right click menu): it and what is wired after it run for real;
        the flow's inputs are their defaults, the first trigger's Start box gives what it gave last time."""
        await self._boxes.sync()
        problem = self._problem()
        if problem:
            ui.notify(problem, type="warning")
            return
        start = next((t.id for t in self._draft.triggers if self._last_start(t.id)[0]), START)
        event = self._last_start(start)[1] or {}
        self._show_test(*await self._runner.test_run(self._draft.to_flow(), None, event, start_at=node_id,
                                                     start=start))

    def _show_test(self, results: list[dict], error: Exception | None) -> None:
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
