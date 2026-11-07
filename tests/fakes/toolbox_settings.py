from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.alerts.alert_store import AlertStore
from streamer_toolbox.core.deck.deck_images import DeckImages
from streamer_toolbox.core.deck.deck_store import DeckStore
from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.exports.export_finder import ExportFinder
from streamer_toolbox.core.exports.export_importer import ExportImporter
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.variables.variable_store import VariableStore
from streamer_toolbox.core.widgets.widget_store import WidgetStore


class ToolboxSettings:
    """A settings folder's stores in a folder of a test (one toolbox), with its export finder and importer."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.actions = ActionRegistry()
        self.actions.add("sound.play", lambda file="": None, "Plays a sound", "Play sound")
        self.variables = VariableStore(folder / "variables")
        self.flows = FlowLibrary(FlowStore(folder / "flows"), FlowStore(folder / "templates"),
                                 FlowRunner(self.actions, self.variables), self.actions)
        self.flows.load()
        self.alerts = AlertStore(folder / "alerts.json")
        self.widgets = WidgetStore(folder / "widgets")
        self.events = EventTypeStore(folder / "event_types.json")
        self.deck = DeckStore(folder / "live_deck.json", lambda: [])
        self.deck_images = DeckImages(folder / "deck_images")
        self.finder = ExportFinder(self.flows, self.alerts, self.widgets, self.events, self.variables, self.deck,
                                   self.deck_images, self.actions)
        self.importer = ExportImporter(self.flows, self.alerts, self.widgets, self.events, self.variables,
                                       self.deck, self.deck_images, self.actions, folder / "media")
