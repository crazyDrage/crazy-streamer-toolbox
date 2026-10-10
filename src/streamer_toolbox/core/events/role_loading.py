from collections.abc import MutableMapping
from typing import Any

CHAT, START, EVERY = "chat", "start", "every"
MODES = (CHAT, START, EVERY)
MODE_KEY = "role_loading_mode"  # in `choice`: one of MODES
MINUTES_KEY = "role_loading_minutes"  # in `choice`: how often, for the mode EVERY


class RoleLoading:
    """When the toolbox loads who is a mod, a VIP or a sub (Settings → Viewer roles), so a trigger's role
    filter is right without a request per trigger:

    CHAT: never; a viewer's role is only what their last chat message said. START: the lists are loaded once
    when the toolbox starts (as soon as Twitch is connected). EVERY: at the start and again every `minutes`.
    A chat message always corrects the loaded role of the viewer who wrote it.

    `choice` keeps it (the GUI's general storage)."""

    def __init__(self, choice: MutableMapping[str, Any]) -> None:
        self._choice = choice

    @property
    def mode(self) -> str:
        mode = self._choice.get(MODE_KEY, CHAT)
        return mode if mode in MODES else CHAT

    def set_mode(self, mode: str) -> None:
        if mode not in MODES:
            raise ValueError(f"mode must be one of {', '.join(MODES)}, not {mode!r}")
        self._choice[MODE_KEY] = mode

    @property
    def minutes(self) -> int:
        try:
            return max(int(self._choice.get(MINUTES_KEY, 10)), 1)
        except (TypeError, ValueError):
            return 10

    def set_minutes(self, minutes: Any) -> None:
        try:
            self._choice[MINUTES_KEY] = max(int(minutes), 1)
        except (TypeError, ValueError):
            raise ValueError("how many minutes? a whole number, 1 or more") from None
