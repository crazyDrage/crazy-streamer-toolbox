import inspect
from collections.abc import Callable
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.alerts.boxes.alert_box import PICTURE_TYPES
from streamer_toolbox.core.event_types.event_flows import ONLY_TO, action_name
from streamer_toolbox.core.event_types.event_sender import EventSender
from streamer_toolbox.core.event_types.event_type import EventType
from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.files.file_types import AUDIO_TYPES

FILES = {"picture": PICTURE_TYPES, "sound": AUDIO_TYPES}


class EventActions:
    """The Events boxes (his round 78): one per event type, `event.send.<name>`, "Send <name>", a field per value
    and "Only to". It sends the event to every widget and alert that uses it (EventSender). The event types
    change → the boxes are made again (like the alerts' boxes). choices(event): what "Only to" offers
    ({"widget chat_box": "Widget chat_box", ...})."""

    def __init__(self, events: EventTypeStore, sender: EventSender,
                 choices: Callable[[str], dict[str, str]]) -> None:
        self._events = events
        self._sender = sender
        self._choices = choices
        self._actions: ActionRegistry | None = None
        self._made: set[str] = set()

    def add_to(self, actions: ActionRegistry) -> None:
        self._actions = actions
        self.sync()

    def sync(self) -> None:
        if self._actions is None:
            return
        for name in self._made:
            self._actions.remove(name)
        self._made = set()
        for kind in self._events.all():
            self._add(kind)

    def _add(self, kind: EventType) -> None:
        name = kind.name

        async def send(**values: Any) -> dict[str, Any]:
            only_to = str(values.pop(ONLY_TO, "") or "")
            return await self._sender.send(name, values, only_to)

        async def choices() -> dict[str, str]:
            return {"": "Every widget and alert that uses it", **self._choices(name)}

        fields = [v.name for v in kind.values if v.name != ONLY_TO]
        send.__signature__ = inspect.Signature(
            [inspect.Parameter(field, inspect.Parameter.KEYWORD_ONLY, default="") for field in fields]
            + [inspect.Parameter(ONLY_TO, inspect.Parameter.KEYWORD_ONLY, default="")])
        self._actions.add(action_name(name), send,
                          f"Sends the event {name!r} (Overlay → Events) to every widget and alert that uses it; "
                          "a value left empty is its default. Only to: one widget or alert only. Gives how many "
                          "widget pages got it and how many alerts play", f"Send {name}", group="Events",
                          options={ONLY_TO: choices}, labels={ONLY_TO: "Only to"},
                          outputs={"pages": "number", "alerts": "number", "in_front": "number"},
                          hints={v.name: f"empty: {v.default}" for v in kind.values if v.default},
                          files={v.name: FILES[v.kind] for v in kind.values if v.kind in FILES})
        self._made.add(action_name(name))
