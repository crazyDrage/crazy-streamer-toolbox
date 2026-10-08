from collections.abc import Callable
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry

from .pretend_lamp import COLORS, PretendLamp


class LampActions:
    """The lamp's BOXES. One class holds a group of boxes; `add_to` registers them.

    How a box is made:
      - It is one `async` method. Its parameters are the box's fields in the flow editor. A parameter with a
        default (`times: int = 3`) is optional; the type (`int`, `float`, `bool`, `str`) decides the input.
      - What it returns is the box's result. Return a dict, and name its keys in `outputs=`: each key
        becomes a dot other boxes can wire from. `-> None` means the box has no result.
      - To refuse, `raise` with words the streamer understands. The text shows on the box.
      - The same action is also a button on the Live page, a button in the SAMMI deck, and
        `POST /action/example.set_color` in the API. You write it once.

    `need_on` is given by the connection: it raises while the lamp is switched off, so every box says the
    same clear thing then. `blinked` is given by the plugin: it tells the toolbox "the lamp blinked"."""

    def __init__(self, lamp: PretendLamp, need_on: Callable[[], None],
                 blinked: Callable[[dict[str, Any]], None]) -> None:
        self._lamp = lamp
        self._need_on = need_on
        self._blinked = blinked

    def add_to(self, actions: ActionRegistry) -> None:
        # actions.add(name, method, what it does, the box's title, extras...)
        # The name is "<plugin id>.<what>". Saved flows hold it: never rename one that people use.
        actions.add("example.switch", self.switch, "Switches the lamp on or off", "Switch lamp")

        # options= gives a field a PICKER. The value is an async function that returns the choices: it is
        # called when the box's form opens, so it can ask the running program what it has right now.
        # outputs= names the keys of the result. hints= puts one line of help under a field.
        actions.add("example.set_color", self.set_color, "Changes the lamp's colour", "Set lamp colour",
                    options={"color": self.color_names}, outputs={"color": "text", "before": "text"},
                    hints={"color": "One of the lamp's colours"})

        # group= sorts boxes into a sub list in the Add box window.
        actions.add("example.blink", self.blink, "Blinks the lamp; the flow waits until it is done",
                    "Blink lamp", group="Effects", outputs={"blinks": "number"},
                    hints={"times": "How often", "seconds": "How long each half takes, e.g. 0.3"})

        # live=True: a box without fields that only reads. Any field of any box can then use it as a
        # "Live value", so it is read at the moment the flow runs.
        actions.add("example.get_color", self.get_color, "The lamp's colour now", "Get lamp colour",
                    live=True, outputs={"color": "text", "on": "yes/no"})

    async def color_names(self) -> list[str]:
        return list(COLORS)

    async def switch(self, on: bool = True) -> None:
        self._need_on()
        self._lamp.switch(on)

    async def set_color(self, color: str) -> dict[str, str]:
        self._need_on()
        before = self._lamp.set_color(str(color).strip().lower())
        return {"color": self._lamp.color, "before": before}

    async def blink(self, times: int = 3, seconds: float = 0.3) -> dict[str, int]:
        self._need_on()
        times = int(times)
        if not 1 <= times <= 20:
            raise ValueError("Blink between 1 and 20 times")
        await self._lamp.blink(times, max(float(seconds), 0.05))
        self._blinked({"times": times, "color": self._lamp.color})  # → the trigger "Example lamp blinked"
        return {"blinks": self._lamp.blinks}

    async def get_color(self) -> dict[str, Any]:
        self._need_on()
        return {"color": self._lamp.color, "on": self._lamp.on}
