"""The plugin's entry point: everything it adds to the toolbox is collected in register()."""
from streamer_toolbox.core.interfaces.plugin_context import PluginContext
from streamer_toolbox.core.interfaces.toolbox_plugin import ToolboxPlugin

from .lib.deck_board import DeckBoard
from .lib.deck_layouts import DeckLayouts


class SammiDecksPlugin(ToolboxPlugin):
    """A Deck Hopper alternative on the Tools page: SAMMI's decks and buttons, a tap presses one."""

    def register(self, ctx: PluginContext) -> None:
        layouts = DeckLayouts()  # one for every open tab: SAMMI's deck file is read once per change
        images: dict[str, str] = {}  # SAMMI's picture folder → its URL (served once)
        ctx.add_tool("SAMMI decks", lambda: DeckBoard(ctx, layouts, images).build(), icon="grid_view",
                     description="Your SAMMI decks as buttons: pick a deck, tap a button to press it in SAMMI")
