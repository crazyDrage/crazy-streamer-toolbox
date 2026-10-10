from typing import Any

from streamer_toolbox.core.events.event_fields import EVENT_FIELDS
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.number_match import compare_of

# what a test start fills in when the flow never started for real yet (his trigger's own values come first)
EXAMPLES: dict[str, Any] = {
    "user": "TestViewer", "user_login": "testviewer", "user_id": "12345", "input": "hello", "cost": 100, "message": "hello chat",
    "args": "", "role": "viewer", "platform": "twitch", "tier": "1000", "months": 3, "amount": 5, "bits": 100,
    "viewers": 10, "seconds": 60, "anonymous": False, "gift": False, "automatic": False, "source": "test",
    "reward_id": "", "redemption_id": "test", "message_id": "test", "model": "", "key": "f23", "followed_at": "2026-01-01T12:00:00Z",
    "title": "My stream", "category": "Just Chatting", "bpm": 80,
}


class StartExamples:
    """The values a test start gives the Start box: one per field its triggers give (EVENT_FIELDS), taken from
    the last real start when there was one, else from the trigger itself (its reward, command, custom trigger
    name, ...), else an example (TestViewer, hello, 100, ...)."""

    @staticmethod
    def fields(triggers: list[FlowTrigger]) -> list[str]:
        names: dict[str, None] = {}
        for trigger in triggers:
            for name in EVENT_FIELDS.get(trigger.kind, ()):
                names.setdefault(name, None)
        return list(names)

    @classmethod
    def values(cls, triggers: list[FlowTrigger], last: dict[str, Any] | None) -> dict[str, Any]:
        from_triggers: dict[str, Any] = {}
        for trigger in triggers:
            for key, value in trigger.match.items():
                if isinstance(value, str) and "*" not in value and compare_of(value) is None \
                        and key not in ("who", "who_max", "roles", "words"):
                    from_triggers.setdefault(key, value)
        last = last or {}
        return {name: last[name] if name in last else from_triggers.get(name, EXAMPLES.get(name, ""))
                for name in cls.fields(triggers)}
