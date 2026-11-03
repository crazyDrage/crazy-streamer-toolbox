from abc import ABC
from collections.abc import Callable, Collection
from typing import Any, Optional

from streamer_toolbox.core.actions.registered_action import OptionsProvider


class Trigger(ABC):
    """Something that can start a flow: it shows in the Add trigger window, and `fire(data)` starts every flow
    that has it.

        class LampBlinked(Trigger):
            event = "blinked"
            title = "Example lamp blinked"
            fields = ("times", "color")

        blinked = LampBlinked()
        ctx.add(blinked)
        ...
        blinked.fire({"times": 3, "color": "red"})

    `event` is its name; the plugin's id goes in front by itself ("example.blinked"). `fields` are the keys its
    data always has: the dots a flow wires from. `pick` is the field a flow's trigger is matched on (empty:
    the first) and `example` what that input starts with (* = any). `choices` makes that input a dropdown: a
    list, or an async function that returns one (set it in __init__ then). Typing still works."""

    event: str = ""
    title: str = ""
    fields: tuple[str, ...] = ()
    icon: str = "bolt"
    pick: str = ""
    example: str = "*"
    description: str = ""     # its line under the title in the Add trigger window
    choices: OptionsProvider | Collection[str] | None = None

    _publish: Optional[Callable[[str, dict[str, Any]], None]] = None

    def fire(self, data: dict[str, Any]) -> None:
        """It happened: flows with this trigger start, with `data` on their dots."""
        if self._publish is None:
            raise RuntimeError(f"the trigger {self.event!r} isn't added yet (ctx.add)")
        self._publish(self.event, data)

    def added(self, publish: Callable[[str, dict[str, Any]], None]) -> None:
        """Called by ctx.add: from now on fire() reaches the toolbox."""
        self._publish = publish
