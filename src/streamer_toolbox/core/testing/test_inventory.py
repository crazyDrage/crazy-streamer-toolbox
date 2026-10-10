import re
from collections.abc import Iterable

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.left_out import owners
from streamer_toolbox.core.testing.test_item import (BOX, CONNECTION, KIND_FOLDERS, PAGE, PAGE_FILE, TOOL, TRIGGER,
                                                     TestItem)

OWN_FLOWS = "flow"  # the category of his own flows as boxes: his data, not part of the toolbox
NO_GROUP = "general"  # the file of a category's boxes that are in no sub group
STEP = " > "  # between the steps of a file's heading: "Flows > Boxes > OBS > Scenes"
Menu = Iterable[tuple[str, str, Iterable[tuple[str, str]]]]


class TestInventory:
    """Everything of this toolbox that has to be tested, as one list, in the order of the side menu: every
    main tab's pages, and below the tab they are reached from every trigger and box (Flows), every tool (Tools)
    and every connection (Connections). His own flows and the parked boxes are not in it.

    Each gets its file in the test record, as deep as the menu and the Add windows go:

        <tab>/page                         the tab's own page and the pages below it in the menu
        flows/triggers/<program>           the Add trigger window's groups
        flows/boxes/<category>/<group>     the Add box window's categories and their sub groups
        tools/<tool>, connections/<id>

    `menu` is (tab title, address, [(title, address) of the pages below it]); `triggers` is kind → (title,
    its group in the Add trigger window); `folders` names a connection's box category where they differ
    ("vtube_studio" → "vts")."""

    __test__ = False  # not a test class, whatever its name says to a test runner

    def __init__(self, actions: ActionRegistry, connections: Iterable[tuple[str, str]], tools: Iterable[str],
                 triggers: dict[str, tuple[str, str]], folders: dict[str, str] | None = None,
                 menu: Menu = ()) -> None:
        self._actions = actions
        self._connections = list(connections)  # (id, title)
        # a box category → its connection, where they differ (folders: "vtube_studio" → "vts")
        self._connection_of = {category: cid for cid, category in (folders or {}).items()}
        self._tools = list(tools)  # titles
        self._triggers = triggers
        self._menu = [(title, address, list(below)) for title, address, below in menu]

    def items(self) -> list[TestItem]:
        tabs = [title for title, _, _ in self._menu]
        items: list[TestItem] = []
        for tab in [*tabs, *(t for t in ("Flows", "Tools", "Connections") if t not in tabs)]:
            items += self._pages(tab)
            if tab == "Flows":
                items += self._trigger_items() + self._boxes()
            elif tab == "Tools":
                items += [TestItem(TOOL, slug(title), title, file=f"{KIND_FOLDERS[TOOL]}/{slug(title)}",
                                   heading=f"Tools{STEP}{title}") for title in self._tools]
            elif tab == "Connections":
                items += [TestItem(CONNECTION, cid, title, file=f"{KIND_FOLDERS[CONNECTION]}/{cid}",
                                   heading=f"Connections{STEP}{title}") for cid, title in self._connections]
        return items

    def _pages(self, tab: str) -> list[TestItem]:
        return [TestItem(PAGE, page_address, page_title, tab, file=f"{slug(tab)}/{PAGE_FILE}", heading=tab)
                for title, address, below in self._menu if title == tab
                for page_title, page_address in [(title, address), *below]]

    def _trigger_items(self) -> list[TestItem]:
        items = [TestItem(TRIGGER, kind, title, group,
                          file=f"{KIND_FOLDERS[TRIGGER]}/{self._trigger_file(kind, group)}",
                          heading=f"Flows{STEP}Triggers{STEP}{group}")
                 for kind, (title, group) in self._triggers.items()]
        return sorted(items, key=lambda item: (item.file, item.title.casefold()))

    def _trigger_file(self, kind: str, group: str) -> str:
        """A program's triggers ("twitch.chat") go by its connection, the others by their group's name."""
        owner = owners(kind)[0]
        return self._connection_of.get(owner, owner) if "." in kind else slug(group)

    def _boxes(self) -> list[TestItem]:
        items = []
        for a in self._actions.all(include_flow_only=True):
            if a.category == OWN_FLOWS:
                continue
            folder = self._connection_of.get(a.category, a.category)
            items.append(TestItem(
                BOX, a.name, a.title, a.category_title, a.group,
                f"{KIND_FOLDERS[BOX]}/{folder}/{slug(a.group) or NO_GROUP}",
                STEP.join(["Flows", "Boxes", a.category_title, *([a.group] if a.group else [])])))
        return sorted(items, key=lambda item: (item.file, item.title.casefold()))


def slug(title: str) -> str:
    """A title as it is in an address or a file name ("SAMMI decks" → "sammi_decks"); a tool's id in the test
    list."""
    return re.sub(r"[^a-z0-9]+", "_", title.casefold()).strip("_")
