import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from streamer_toolbox.core.alerts import alert_starters
from streamer_toolbox.core.alerts.alert_input import AlertInput
from streamer_toolbox.core.alerts.alert_rule import AlertRule, default_parts

PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")


class AlertStore:
    """The Alerts tool's list in config/alerts.json, in his order (his round 65: his own alerts, own names and
    inputs). A toolbox without the file starts with the usual ones (alert_starters.FIRST), off.

    The file from before round 65 had one alert per event ({"twitch.follow": {...}}); it is read as those
    alerts, each with the inputs its event gave (and any other field of the event its words used).

    `unstarted`: the alerts a new toolbox (or one from before round 65) starts with, as (alert, event); their
    events get their flows (EventUsers.start), then started() writes the file, so it happens once.
    on_change() after every change."""

    def __init__(self, path: Path) -> None:
        self._path = path
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        saved = data.get("alerts", {})
        # off: a restart clears the alerts waiting in line; on: AlertBackup keeps them in a file
        self.keep_through_restart = bool(data.get("keep_through_restart", False))
        self.on_change: Callable[[], None] | None = None
        self.unstarted: list[tuple[AlertRule, str]] = []
        self._before = ""  # the file from before round 65, as it was
        if isinstance(saved, list):
            self._rules = {r.id: r for r in (AlertRule.from_dict(d) for d in saved if isinstance(d, dict) and d.get("id"))}
        else:  # no file yet, or the one from before round 65 (kept as it was, next to it: see started)
            self._before = path.read_text(encoding="utf-8") if path.is_file() else ""
            self._rules = {}
            for event, starter in alert_starters.OLD_EVENTS.items():
                rule = _old(starter, saved[event]) if event in saved else AlertRule.starter(starter)
                self._rules[rule.id] = rule
                self.unstarted.append((rule, starter))

    def all(self) -> list[AlertRule]:
        return list(self._rules.values())

    def get(self, id_: str) -> AlertRule | None:
        return self._rules.get(id_)

    def save(self, rule: AlertRule) -> None:
        """Changes the alert with its id, or adds it last."""
        self._rules[rule.id] = rule
        self._write()

    def add(self, name: str, inputs: tuple[AlertInput, ...] = (), text: str = "", event: str = "") -> AlertRule:
        """A new alert, off, last in the list, with an id from its name that no other alert has, playing on that
        event type (its inputs follow the event's values: EventUsers)."""
        if not text and any(i.name == "user" for i in inputs):
            text = "{user}"
        rule = AlertRule(self.free_id(name), name.strip() or "New alert", inputs, text=text,
                         parts=default_parts(inputs), event=event)
        self.save(rule)
        return rule

    def delete(self, id_: str) -> None:
        if self._rules.pop(id_, None) is not None:
            self._write()

    def free_id(self, name: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "_", name.casefold()).strip("_") or "alert"
        id_, n = base, 2
        while id_ in self._rules:
            id_, n = f"{base}_{n}", n + 1
        return id_

    def started(self) -> None:
        """The starting flows are made: write the list, so they aren't made again. A file from before round 65
        stays as it was in alerts.before_round_65.json."""
        self.unstarted = []
        old = self._path.with_name("alerts.before_round_65.json")
        if self._before and not old.exists():
            old.write_text(self._before, encoding="utf-8")
        self._write()

    def keep_copy(self, name: str) -> None:
        """The file as it is now, kept next to it under that name (once: a copy that is there stays)."""
        copy = self._path.with_name(name)
        if self._path.is_file() and not copy.exists():
            copy.write_text(self._path.read_text(encoding="utf-8"), encoding="utf-8")

    def set_keep_through_restart(self, on: bool) -> None:
        self.keep_through_restart = on
        self._write()

    def _write(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {"alerts": [r.to_dict() for r in self._rules.values()]}
        if self.keep_through_restart:
            data["keep_through_restart"] = True
        self._path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        if self.on_change is not None:
            self.on_change()


def _old(starter: str, data: dict[str, Any]) -> AlertRule:
    """An alert from the file before round 65: its settings, its event's inputs, and an input for every other
    field of the event its words use ({bits} in a Cheer alert)."""
    rule = AlertRule.starter(starter)
    inputs = list(rule.inputs)
    words = " ".join([str(data.get("text", rule.text))] + [str(p.get("text", "")) for p in data.get("pieces", [])
                                                           if isinstance(p, dict)]
                     + [str(v.get("text", "")) for v in data.get("variations", []) if isinstance(v, dict)])
    for name in dict.fromkeys(PLACEHOLDER.findall(words)):
        extra = alert_starters.OLD_FIELDS.get(starter, {}).get(name)
        if extra and rule.input(name) is None:
            inputs.append(AlertInput(name, extra[0], extra[1]))
    return AlertRule.from_dict({**data, "id": rule.id, "name": rule.name, "text": data.get("text", rule.text),
                                "inputs": [i.to_dict() for i in inputs], "event": starter})

