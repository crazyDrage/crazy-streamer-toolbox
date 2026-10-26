from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.deck.deck_images import DeckImages
from streamer_toolbox.core.deck.deck_store import DeckStore
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.gui.components.live_deck.live_deck_view import LiveDeckView
from streamer_toolbox.gui.services.activity_log import ActivityLog


class LivePage:
    """What he uses while streaming: the deck (pages of buttons he placed himself, like a SAMMI deck) and
    nothing else (his answer of 2026-10-14: "Recent" and the plugins' cards went; a plugin's cards are under
    Plugins → that plugin)."""

    def __init__(self, actions: ActionRegistry, activity: ActivityLog, deck: DeckStore, flows: FlowLibrary,
                 images: DeckImages) -> None:
        self._actions = actions
        self._activity = activity
        self._deck = deck
        self._flows = flows
        self._images = images

    def build(self) -> None:
        LiveDeckView(self._deck, self._actions, self._flows, self._activity, self._images).build()

    def build_bare(self) -> None:
        """/live/buttons: the deck on its own, without the toolbox around it (his round 63; for a tablet)."""
        LiveDeckView(self._deck, self._actions, self._flows, self._activity, self._images, bare=True).build()
