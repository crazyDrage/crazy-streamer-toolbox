import logging
from typing import Any

from streamer_toolbox.core.alerts.alert_queue import AlertQueue
from streamer_toolbox.core.alerts.alert_rule import ALERT_EVENTS
from streamer_toolbox.core.alerts.alert_store import AlertStore

log = logging.getLogger(__name__)
# a common event (CommonEvents) → the alert it shows. Twitch's own events show theirs directly, so the common
# one only counts when it came from another platform: a follow is never shown twice
COMMON = {"follow": "twitch.follow", "sub": "twitch.sub", "resub": "twitch.resub", "gift": "twitch.gift",
          "cheer": "twitch.cheer", "raid": "twitch.raid"}


class AlertRouter:
    """EventBus → alerts: a follow, sub, cheer or raid whose rule in the Alerts tool is on (and big enough) goes
    into the alert line. Flows with the same trigger run as well; this is the no-flow way. The rules are one
    per kind of event, for every platform: a Rumble follow or a YouTube membership shows the Follow / Sub alert
    too (they arrive as the common events `follow`, `sub`, ...)."""

    def __init__(self, store: AlertStore, queue: AlertQueue) -> None:
        self._store = store
        self._queue = queue

    async def handle(self, kind: str, data: dict[str, Any]) -> None:
        if kind in COMMON:
            if data.get("platform") == "twitch":
                return
            kind = COMMON[kind]
        rule = self._store.get(kind)
        if rule is None or not rule.wants(data):
            return
        try:
            await self._queue.show(rule.alert_for(data))
        except FileNotFoundError as e:  # a picture that was moved: say it, the stream goes on
            log.warning("alert for %s not shown: %s", kind, e)

    async def test(self, event: str, amount: int | None = None) -> int:
        """The Test button: the rule's alert with example data, also when the rule is off. amount: as if that
        many bits / viewers / gifts came (a variation's Test)."""
        rule = self._store.get(event)
        if rule is None:
            raise KeyError(f"there are no alerts for {event!r}")
        example = dict(ALERT_EVENTS[event][3])
        if amount is not None and rule.has_amount:
            example[ALERT_EVENTS[event][2]] = amount
        return await self._queue.show(rule.alert_for(example))
