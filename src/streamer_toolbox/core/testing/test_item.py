from dataclasses import dataclass

PAGE, TRIGGER, BOX, TOOL, CONNECTION = "page", "trigger", "box", "tool", "connection"
KIND_TITLES = {PAGE: "Pages", TRIGGER: "Triggers", BOX: "Boxes", TOOL: "Tools", CONNECTION: "Connections"}
# where a kind's files are in the test record (docs/tested/), below the main tab they are reached from
KIND_FOLDERS = {BOX: "flows/boxes", TRIGGER: "flows/triggers", TOOL: "tools", CONNECTION: "connections"}
PAGE_FILE = "page"  # <main tab>/page.md: the tab's own pages


@dataclass(frozen=True)
class TestItem:
    """One thing of the toolbox that has to be tested before a build offers it: a page, a trigger, a box, a
    tool or a connection. `id` is its name in the code (a page's address, a trigger's kind, a box's action
    name, a tool's slug, a connection's id); `area` is the title of where it belongs (the page's main tab, the
    box's category, the trigger's program) and `group` its sub group. `file` is its file in the test record
    without the ending, sorted like the menu ("flows/boxes/obs/scenes"), and `heading` that file's title."""

    __test__ = False  # not a test class, whatever its name says to a test runner

    kind: str
    id: str
    title: str
    area: str = ""
    group: str = ""
    file: str = "toolbox"
    heading: str = ""

    @property
    def key(self) -> str:
        """What the test list files it under, e.g. "box:obs.set_scene"."""
        return f"{self.kind}:{self.id}"
