from nicegui import ui

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.box_filter_store import BoxFilterStore
from streamer_toolbox.gui.components.flow_editor.action_picker import SwitchedOff
from streamer_toolbox.core.actions.registered_action import OptionsProvider
from streamer_toolbox.core.events.last_events import LastEvents
from streamer_toolbox.core.files.box_value_files import BoxValueFiles
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.testing.test_view import TestView
from streamer_toolbox.core.variables.variable_store import VariableStore
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft
from streamer_toolbox.gui.components.flow_editor.flow_editor import FlowEditor


class FlowEditorPage:
    """Create or edit one flow: name, inputs, triggers, and the steps in a list or as boxes with wires (switch
    any time; both edit the same flow file). /flows/edit?flow=<name>, ?template=<name> or nothing for a new one."""

    def __init__(self, library: FlowLibrary, actions: ActionRegistry, runner: FlowRunner,
                 variables: VariableStore, box_files: BoxValueFiles,
                 trigger_choices: dict[str, OptionsProvider] | None = None,
                 box_filters: BoxFilterStore | None = None, switched_off: SwitchedOff | None = None,
                 last_events: LastEvents | None = None, test_view: TestView | None = None) -> None:
        self._last_events = last_events
        self._test_view = test_view
        self._library = library
        self._actions = actions
        self._runner = runner
        self._variables = variables
        self._box_files = box_files
        self._trigger_choices = trigger_choices
        self._box_filters = box_filters
        self._switched_off = switched_off

    def build(self) -> None:
        query = ui.context.client.request.query_params
        old_name = query.get("flow")
        if old_name:
            flow = self._library.get(old_name)
            if flow is None:
                ui.label(f"There's no flow {old_name!r}.").classes("text-negative")
                ui.link("Back to Flows", "/flows")
                return
            draft = FlowDraft.from_flow(flow)
        elif query.get("template"):
            template = next((t for t in self._library.templates() if t.name == query["template"]), None)
            if template is None:
                ui.label(f"There's no template {query['template']!r}.").classes("text-negative")
                return
            draft = FlowDraft.from_flow(template)
            draft.name = ""
        else:
            draft = FlowDraft("", "New flow")
        FlowEditor(draft, old_name, self._library, self._actions, self._runner, self._variables,
                   self._box_files, self._trigger_choices, self._box_filters,
                   self._switched_off, self._last_events, self._test_view).build()
