from streamer_toolbox.core.alerts.boxes.alert_box import AlertBox


class ClearAlerts(AlertBox):
    name = "clear"
    label = "Clear alerts"
    help = "Empties the alert line and takes the alert that is showing away; gives how many were dropped"
    group = "Alerts"

    async def run(self) -> int:
        return self._queue.clear()
