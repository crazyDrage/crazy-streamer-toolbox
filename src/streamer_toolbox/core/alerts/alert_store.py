import json
from pathlib import Path

from streamer_toolbox.core.alerts.alert_rule import ALERT_EVENTS, AlertRule


class AlertStore:
    """The Alerts tool's settings in config/alerts.json: one AlertRule per kind of event, in the tool's order.
    A kind that isn't in the file yet has its starting text and is off, so nothing shows until he switches it on."""

    def __init__(self, path: Path) -> None:
        self._path = path
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        saved = data.get("alerts", {})
        self._rules = {event: AlertRule.from_dict(event, saved[event]) if event in saved
                       else AlertRule.default(event) for event in ALERT_EVENTS}

    def all(self) -> list[AlertRule]:
        return list(self._rules.values())

    def get(self, event: str) -> AlertRule | None:
        return self._rules.get(event)

    def save(self, rule: AlertRule) -> None:
        if rule.event not in ALERT_EVENTS:
            raise KeyError(f"there are no alerts for {rule.event!r}")
        self._rules[rule.event] = rule
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps({"alerts": {e: r.to_dict() for e, r in self._rules.items()}}, indent=2,
                                         ensure_ascii=False), encoding="utf-8")
