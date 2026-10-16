from collections.abc import Iterable, Mapping, MutableMapping
from typing import Any

from streamer_toolbox.core.actions.registered_action import RegisteredAction
from streamer_toolbox.core.testing.test_inventory import OWN_FLOWS
from streamer_toolbox.core.testing.test_item import BOX, CONNECTION, TOOL, TRIGGER, TestItem
from streamer_toolbox.core.testing.test_list import CHECKS, FLAGS, TestList

NORMAL, TESTING = "normal", "testing"
MODES = (NORMAL, TESTING)
# what the choice held before 2026-10-11: "tested" is NORMAL, "everything" is NORMAL with no check ticked
OLD_TESTED, OLD_EVERYTHING = "tested", "everything"
MODE_KEY = "test_view_mode"  # in `choice`: one of MODES
MAY_NOT_KEY = "test_view_may_not"  # in `choice`: the ticked ones of MAY_NOT
# what the choice held before 2026-10-12: the checks a thing had to have (NORMAL) or that hid it (TESTING)
NEEDED_KEY = "test_view_needed"
# the three ticks, named by what they let in: a thing that misses that check
MAY_NOT = {"works": "May not work", "understandable": "May not be understandable", "usable": "May not be usable"}
DISCONNECTED_KEY = "test_view_disconnected"  # in `choice`: True = also what belongs to a connection that is off
# they take a value and give it (Debug also shows it): they stay in the testing mode, to feed and read the others
HELPER_BOXES = ("logic.debug", "logic.value")
WHY = {NORMAL: "not tested yet", TESTING: "done already (testing mode)"}


class TestView:
    """What of the toolbox he sees, by his three checks: which boxes the Add box window offers, which triggers
    the Add trigger window, which tools the Tools page, which connections the Connections page. Flows that
    already use a thing keep it and keep running, and a hidden connection stays connected. Pages are never hidden.

    Two modes and three ticks (Settings → What you see; his layout of 2026-10-11, the ticks' names of
    2026-10-12). A tick is named by what it lets in: "May not work" is what misses the Works check, and so on
    (MAY_NOT). NORMAL shows what is done, and also what a tick lets in: a thing is shown when every check it
    misses is ticked (no tick: only what has all three; at first what works). TESTING shows only what a tick
    names: what misses one of the ticked checks (no tick counts as all three), plus the Debug and the Value
    box. His own flows as boxes are always shown: they are his, not the toolbox's.

    `disconnected` is a fourth tick of another kind: with it, the boxes and triggers of a connection that is
    switched off are offered too (without it they are left out, see assemble's switched_off).

    `choice` keeps all of it (the GUI's general storage)."""

    __test__ = False  # not a test class, whatever its name says to a test runner

    def __init__(self, tested: TestList, choice: MutableMapping[str, Any]) -> None:
        self._tested = tested
        self._choice = choice

    @property
    def mode(self) -> str:
        mode = self._choice.get(MODE_KEY, NORMAL)
        return mode if mode in MODES else NORMAL

    def set_mode(self, mode: str) -> None:
        if mode not in MODES:
            raise ValueError(f"mode must be one of {', '.join(MODES)}, not {mode!r}")
        self._choice[MAY_NOT_KEY] = list(self.may_not)  # a choice of before is kept under today's names
        self._choice[MODE_KEY] = mode

    @property
    def may_not(self) -> tuple[str, ...]:
        """The ticked ones: the checks a shown thing may miss (NORMAL), or the ones looked for (TESTING)."""
        if MAY_NOT_KEY in self._choice:
            ticked = self._choice[MAY_NOT_KEY]
        elif self._choice.get(MODE_KEY) == OLD_EVERYTHING:
            ticked = list(CHECKS)
        else:  # the old ticks: in NORMAL the checks a thing had to have, in TESTING the ones that hid it
            needed = self._choice.get(NEEDED_KEY, ["works"])
            ticked = needed if self.mode == TESTING else [check for check in CHECKS if check not in needed]
        return tuple(check for check in CHECKS if check in ticked)

    def let_in(self, check: str, on: bool) -> None:
        if check not in CHECKS:
            raise ValueError(f"check must be one of {', '.join(CHECKS)}, not {check!r}")
        self._choice[MAY_NOT_KEY] = [c for c in CHECKS if (on if c == check else c in self.may_not)]
        self._choice[MODE_KEY] = self.mode

    @property
    def disconnected(self) -> bool:
        """Whether what belongs to a switched-off connection is offered too."""
        return self._choice.get(DISCONNECTED_KEY) is True

    def set_disconnected(self, on: bool) -> None:
        self._choice[DISCONNECTED_KEY] = bool(on)

    def why(self) -> str:
        """Why something is hidden right now, in a few words; "" when nothing is."""
        return WHY[self.mode] if self.mode == TESTING or len(self.may_not) < len(CHECKS) else ""

    def shows(self, checks: Mapping[str, bool]) -> bool:
        """Whether a thing with these three checks ({"works": True, ...}) is shown."""
        missing = [check for check in CHECKS if not checks.get(check)]
        if self.mode == TESTING:
            return any(check in (self.may_not or CHECKS) for check in missing)
        return all(check in self.may_not for check in missing)

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
