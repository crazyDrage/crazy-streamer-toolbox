from collections.abc import Iterable, Mapping, MutableMapping
from typing import Any

from streamer_toolbox.core.actions.registered_action import RegisteredAction
from streamer_toolbox.core.testing.test_inventory import OWN_FLOWS
from streamer_toolbox.core.testing.test_item import BOX, CONNECTION, TOOL, TRIGGER, TestItem
from streamer_toolbox.core.testing.test_list import CHECKS, FLAGS, TestList

TESTED, EVERYTHING, TESTING = "tested", "everything", "testing"
MODES = (TESTED, EVERYTHING, TESTING)
MODE_KEY = "test_view_mode"  # in `choice`: one of MODES
NEEDED_KEY = "test_view_needed"  # in `choice`: the checks a thing needs to be shown in the mode TESTED
# they take a value and give it (Debug also shows it): they stay in the testing mode, to feed and read the others
HELPER_BOXES = ("logic.debug", "logic.value")
WHY = {TESTED: "not tested yet", TESTING: "done already (testing mode)"}


class TestView:
    """What of the toolbox he sees, by his three checks: which boxes the Add box window offers, which triggers
    the Add trigger window, which tools the Tools page, which connections the Connections page. Flows that
    already use a thing keep it and keep running, and a hidden connection stays connected. Pages are never hidden.

    Three modes (Settings → What you see): TESTED shows what has the checks in `needed` (works alone at first:
    is_tested), EVERYTHING shows all, TESTING shows only what still misses one of the three checks, plus the
    Debug and the Value box. His own flows as boxes are always shown: they are his, not the toolbox's.

    `choice` keeps the mode and the needed checks (the GUI's general storage)."""

    __test__ = False  # not a test class, whatever its name says to a test runner

    def __init__(self, tested: TestList, choice: MutableMapping[str, Any]) -> None:
        self._tested = tested
        self._choice = choice

    @property
    def mode(self) -> str:
        mode = self._choice.get(MODE_KEY, TESTED)
        return mode if mode in MODES else TESTED

    def set_mode(self, mode: str) -> None:
        if mode not in MODES:
            raise ValueError(f"mode must be one of {', '.join(MODES)}, not {mode!r}")
        self._choice[MODE_KEY] = mode

    @property
    def needed(self) -> tuple[str, ...]:
        needed = self._choice.get(NEEDED_KEY, ["works"])
        return tuple(check for check in CHECKS if check in needed)

    def need(self, check: str, on: bool) -> None:
        if check not in CHECKS:
            raise ValueError(f"check must be one of {', '.join(CHECKS)}, not {check!r}")
        self._choice[NEEDED_KEY] = [c for c in CHECKS if (on if c == check else c in self.needed)]

    def why(self) -> str:
        """Why something is hidden right now, in a few words; "" when nothing is."""
        return WHY.get(self.mode, "")

    def shows(self, checks: Mapping[str, bool]) -> bool:
        """Whether a thing with these three checks ({"works": True, ...}) is shown."""
        if self.mode == EVERYTHING:
            return True
        if self.mode == TESTING:
            return not all(checks.get(check) for check in CHECKS)
        return all(checks.get(check) for check in self.needed)

    def shows_box(self, action: RegisteredAction) -> bool:
        if action.category == OWN_FLOWS or (self.mode == TESTING and action.name in HELPER_BOXES):
            return True
        return self.shows({check: getattr(action, flag) for check, flag in FLAGS.items()})

    def shows_key(self, key: str) -> bool:
        """The same for a row of the test record ("trigger:twitch.follow", "tool:points", "connection:obs")."""
        if self.mode == TESTING and key in {f"{BOX}:{name}" for name in HELPER_BOXES}:
            return True
        return self.shows(self._tested.checks(key))

    def shown(self, items: Iterable[TestItem]) -> dict[str, tuple[int, int]]:
        """How many of the boxes, triggers, tools and connections are shown now: kind → (shown, of)."""
        counts = {kind: [0, 0] for kind in (BOX, TRIGGER, TOOL, CONNECTION)}
        for item in items:
            if item.kind in counts:
                counts[item.kind][0] += self.shows_key(item.key)
                counts[item.kind][1] += 1
        return {kind: (shown, of) for kind, (shown, of) in counts.items()}
