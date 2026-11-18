import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from streamer_toolbox.core.deck.deck_button import DeckButton
from streamer_toolbox.core.files.write_whole import write_whole

log = logging.getLogger(__name__)
OFF_WORDS = ("", "false", "0", "off", "no", "none", "null")  # a text value that means off


class DeckStates:
    """What every flow last gave back (its End box's values, its Flow output boxes): a Live button that follows
    one of its flow's outputs (his 11-18: `"active": true` as flow output sets the button's look) reads it here.
    Any run counts, not only a press of the button: the look follows the real thing when something else started
    the flow. `version` goes up with every new value (open Live pages draw again).

    Kept through a restart (his 11-18: "The state should stay after a restart"): one file, on / off of only the
    outputs a button follows (`followed`: (flow name, output) pairs), written when one of them changes. Not
    every value: a flow giving back something big on every chat message would rewrite the file each time."""

    def __init__(self, path: Path, followed: Callable[[], set[tuple[str, str]]]) -> None:
        self._path = path
        self._followed = followed
        self._values: dict[str, dict[str, Any]] = {}  # flow name → output name → its latest value
        self._kept: dict[str, dict[str, bool]] = self._read()  # what the file has: flow → output → on
        self.version = 0

    def heard(self, flow_name: str, outputs: dict[str, Any]) -> None:
        """A run of the flow gave these outputs (FlowRunner.outputs_heard)."""
        if not outputs:
            return
        self._values.setdefault(flow_name, {}).update(outputs)
        self.version += 1
        followed = self._followed()
        changed = False
        for name, value in outputs.items():
            if (flow_name, name) in followed and self._kept.get(flow_name, {}).get(name) != self.means_on(value):
                self._kept.setdefault(flow_name, {})[name] = self.means_on(value)
                changed = True
        if changed:
            self._write()

    def is_on(self, button: DeckButton) -> bool:
        """The button follows an output of its flow and that output's latest value means on. Not heard since the
        start: what the file kept; never heard: off."""
        if not button.state or not button.action.startswith("flow."):
            return False
        flow = button.action[5:]
        if button.state in self._values.get(flow, {}):
            return self.means_on(self._values[flow][button.state])
        return self._kept.get(flow, {}).get(button.state, False)

    @staticmethod
    def means_on(value: Any) -> bool:
        if isinstance(value, str):
            return value.strip().casefold() not in OFF_WORDS
        return bool(value)

    def _read(self) -> dict[str, dict[str, bool]]:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, ValueError) as e:  # a broken file: start with everything off, not a crash
            log.warning("Live button states not read from %s: %s", self._path, e)
            return {}
        return {str(flow): {str(k): bool(v) for k, v in outputs.items()}
                for flow, outputs in data.items() if isinstance(outputs, dict)}

    def _write(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        write_whole(self._path, json.dumps(self._kept, indent=2, ensure_ascii=False))
