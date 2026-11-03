from collections.abc import Callable

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.testing.test_item import BOX, TestItem
from streamer_toolbox.core.testing.test_list import TestList

Items = Callable[[], list[TestItem]]


class TestGate:
    """Ties the toolbox to its test record. Every copy (the project folder and every build) has everything;
    apply() gives each box his three checks and tells the record what there is to test (the files themselves are
    made by devtools/tested). What of it is shown is TestView's (Settings → What you see)."""

    __test__ = False  # not a test class, whatever its name says to a test runner

    def __init__(self, tested: TestList) -> None:
        self.tested = tested
        self.items: Items = list

    def apply(self, actions: ActionRegistry, items: Items) -> None:
        """Once every box, tool and trigger is there. `items` gives the toolbox's whole list of things to test
        (TestInventory)."""
        self.items = items
        found = items()
        for item in found:
            if item.kind == BOX:  # the box carries his three checks (is_tested, ...): TestView shows by them
                actions.mark(item.id, **self.tested.flags(item.key))
        self.tested.take(found)
