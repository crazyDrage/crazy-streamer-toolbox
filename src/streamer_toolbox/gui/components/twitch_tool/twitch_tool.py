from nicegui import ui

from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.interfaces.reward_manager import RewardManager
from streamer_toolbox.core.triggers.custom_trigger_store import CustomTriggerStore
from streamer_toolbox.gui.components.twitch_tool.redeems_tab import RedeemsTab


class TwitchTool:
    """Twitch on the Tools page, with sub tabs: Redeems for now; more tabs go next to it (one class each)."""

    def __init__(self, rewards: RewardManager, flows: FlowLibrary, triggers: CustomTriggerStore) -> None:
        self._rewards = rewards
        self._flows = flows
        self._triggers = triggers

    def build(self) -> None:
        with ui.tabs().props("dense inline-label no-caps align=left").classes("w-full") as tabs:
            redeems = ui.tab("redeems", label="Redeems", icon="redeem")
        with ui.tab_panels(tabs, value=redeems).props("animated=false").classes("w-full bg-transparent"):
            with ui.tab_panel(redeems).classes("p-0 pt-2"):
                RedeemsTab(self._rewards, self._flows, self._triggers).build()
