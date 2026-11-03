from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.alerts.alert_queue import AlertQueue
from streamer_toolbox.core.alerts.boxes.clear_alerts import ClearAlerts
from streamer_toolbox.core.alerts.boxes.show_alert import ShowAlert


class AlertActions:
    """The Alerts boxes: show an alert made on the spot, and empty the line. The alerts of the Alerts tool play
    on their event (his round 78 answer 2 b: "we want to switch to events"): the event's Send box
    (core/event_types), not a box per alert any more.

    One Box class per fixed box, in boxes/."""

    def __init__(self, queue: AlertQueue) -> None:
        self._queue = queue

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (ShowAlert(self._queue), ClearAlerts(self._queue)):
            actions.add_box(box, "alert")
