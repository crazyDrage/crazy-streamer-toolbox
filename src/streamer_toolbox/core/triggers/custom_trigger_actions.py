from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.triggers.custom_trigger import CUSTOM
from streamer_toolbox.core.triggers.custom_trigger_store import CustomTriggerStore


class CustomTriggerActions:
    """Fire custom trigger: from a flow, SAMMI, Kit or the API (POST /action/trigger.fire), e.g. a SAMMI button or a
    YouTube tool says "lizard" with platform youtube; every flow listening to "lizard" starts."""

    def __init__(self, store: CustomTriggerStore, events: EventBus) -> None:
        self._store = store
        self._events = events

    def add_to(self, actions: ActionRegistry) -> None:
        async def names() -> list[str]:
            return self._store.names()

        actions.add("trigger.fire", self.fire, "Fires one of your custom triggers: every flow listening to it starts "
                    "(it doesn't wait for them). The flows get trigger, platform, user, input",
                    "Fire custom trigger", group="Custom triggers", options={"trigger": names},
                    hints={"platform": "Where it came from, e.g. twitch, youtube, sammi (any word; flows can "
                                       "check it)"})

    async def fire(self, trigger: str, platform: str = "", user: str = "", input: str = "") -> str:
        found = self._store.get(str(trigger))
        if found is None:
            raise KeyError(f"there's no custom trigger {trigger!r} (Triggers page)")
        self._events.publish(CUSTOM, {"trigger": found.name, "platform": str(platform), "source": "trigger.fire",
                                      "user": str(user), "input": str(input)})
        return found.name
