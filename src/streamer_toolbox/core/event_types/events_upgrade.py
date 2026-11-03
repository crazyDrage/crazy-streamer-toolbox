from streamer_toolbox.core.event_types.event_conversion import EventConversion
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.upgrades.settings_upgrade import SettingsUpgrade


class EventsUpgrade(SettingsUpgrade):
    """Settings version 1 (round 78): widgets and alerts get event types, and the flows' boxes for a widget's
    input or an alert send that event (EventConversion)."""

    version = 1
    about = "events"

    def __init__(self, conversion: EventConversion) -> None:
        self._conversion = conversion

    def run(self) -> list[str]:
        return self._conversion.run()

    def flow(self, flow: Flow) -> Flow:
        return self._conversion.flow(flow)
