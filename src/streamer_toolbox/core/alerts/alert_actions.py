from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.alerts.alert_queue import AlertQueue
from streamer_toolbox.core.alerts.boxes.clear_alerts import ClearAlerts
from streamer_toolbox.core.alerts.boxes.show_alert import ShowAlert


class AlertActions:
    """The Alerts boxes: show an alert on the overlay (the Browser source in OBS that shows /overlay/alerts),
    empty the line.

    One Box class per box, in boxes/."""

    def __init__(self, queue: AlertQueue) -> None:
        self._queue = queue

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (ShowAlert(self._queue), ClearAlerts(self._queue)):
            actions.add_box(box, "alert")
