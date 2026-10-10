from nicegui import ui

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.deck.deck_store import DeckStore
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.gui.components.live_deck.live_deck_view import LiveDeckView
from streamer_toolbox.gui.services.activity_log import ActivityLog
from streamer_toolbox.gui.services.ui_registry import UiRegistry


class LivePage:
    """What he uses while streaming: the deck (pages of big buttons, like Deck Hopper), then what ran recently and
    the plugins' Live panels."""

    def __init__(self, actions: ActionRegistry, ui_registry: UiRegistry, activity: ActivityLog, deck: DeckStore,
                 flows: FlowLibrary) -> None:
        self._actions = actions
        self._ui = ui_registry
        self._activity = activity
        self._deck = deck
        self._flows = flows

    def build(self) -> None:
        LiveDeckView(self._deck, self._actions, self._flows, self._activity).build()
        with ui.element("div").classes("grid gap-4 w-full lg:grid-cols-3 items-start pt-4"):
            self._recent()
            for _, title, builder in self._ui.panels_for("live"):
                with ui.card().classes("w-full"):
                    ui.label(title).classes("font-semibold")
                    builder()

    def _recent(self) -> None:
        with ui.card().classes("w-full"):
            ui.label("Recent").classes("text-xs uppercase tracking-wide opacity-70")
            shown = {"version": -1}

            @ui.refreshable
            def entries() -> None:
                items = self._activity.entries()[:8]
                if not items:
                    ui.label("Nothing has run yet.").classes("text-sm opacity-60")
                for entry in items:
                    with ui.row().classes("w-full items-start no-wrap gap-2 text-sm"):
                        ui.icon("check_circle" if entry.ok else "error") \
                            .classes("text-positive" if entry.ok else "text-negative").style("margin-top:2px")
                        with ui.column().classes("gap-0 min-w-0"):
                            ui.label(f"{self._title_of(entry.action)}").classes("font-medium")
                            ui.label(f"{entry.time:%H:%M:%S} · {entry.source} · {entry.text}") \
                                .classes("text-xs opacity-70 break-all")

            def refresh_if_changed() -> None:
                if shown["version"] != self._activity.version:
                    shown["version"] = self._activity.version
                    entries.refresh()

            entries()
            ui.timer(1.0, refresh_if_changed)

    def _title_of(self, name: str) -> str:
        return self._actions.get(name).title if name in self._actions else name
