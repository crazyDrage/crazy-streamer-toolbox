from collections.abc import Callable, Iterable

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.left_out import leave_out
from streamer_toolbox.core.testing.test_inventory import slug
from streamer_toolbox.core.testing.test_item import BOX, CONNECTION, PAGE, TOOL, TRIGGER, TestItem
from streamer_toolbox.core.testing.test_list import TestList

Items = Callable[[], list[TestItem]]


class TestGate:
    """Decides what this copy of the toolbox offers, from the test record.

    In the project folder (tested_only False) everything is on, and apply() tells the record what there is to
    test (the files themselves are made by devtools/tested). In a build (tested_only True) only what is tested
    is offered: keeps() answers for a connection while the connections are made, and apply() parks the untested boxes, leaves the
    untested triggers out, takes the untested tools off the list and names the untested pages
    (untested_pages, for the menu)."""

    __test__ = False  # not a test class, whatever its name says to a test runner

    def __init__(self, tested: TestList, tested_only: bool, parked: Iterable[str] = ()) -> None:
        self.tested = tested
        self.tested_only = tested_only
        self._parked = set(parked)  # boxes that are parked anyway (wip_boxes)
        self._untested_connections: set[str] = set()
        self.items: Items = list
        self.untested_pages: set[str] = set()  # their addresses; filled by apply() in a build

    def keeps(self, connection_id: str) -> bool:
        """Whether this copy has that connection at all."""
        if self.tested_only and not self.tested.tested(f"{CONNECTION}:{connection_id}"):
            self._untested_connections.add(connection_id)
            return False
        return True

    def apply(self, actions: ActionRegistry, tools: list[tuple], items: Items) -> None:
        """Once every box, tool and trigger is there. `tools` is the list the Tools page shows (title second);
        `items` gives the toolbox's whole list of things to test (TestInventory)."""
        self.items = items
        if not self.tested_only:
            self.tested.take(items())
            return
        untested = {(item.kind, item.id) for item in items() if not self.tested.tested(item.key)}
        actions.park(self._parked | {name for kind, name in untested if kind == BOX})
        leave_out(self._untested_connections, {name for kind, name in untested if kind == TRIGGER})
        tools[:] = [tool for tool in tools if (TOOL, slug(tool[1])) not in untested]
        self.untested_pages = {name for kind, name in untested if kind == PAGE}
