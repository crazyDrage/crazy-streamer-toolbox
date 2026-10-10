from collections.abc import Callable

from nicegui import ui

from streamer_toolbox.core.testing.test_item import BOX, CONNECTION, TOOL, TRIGGER, TestItem
from streamer_toolbox.core.testing.test_list import CHECKS
from streamer_toolbox.core.testing.test_view import EVERYTHING, TESTED, TESTING, TestView

MODE_TITLES = {TESTED: "Tested", EVERYTHING: "Everything", TESTING: "Testing mode"}
MODE_HELP = {TESTED: "Only what has the checks you pick below.",
             EVERYTHING: "Every box, trigger, tool and connection, tested or not.",
             TESTING: "Only what still misses a check, to go through what is left. The Debug and the Value box stay, "
                      "to give the others a value and to read one."}
KIND_WORDS = {BOX: "boxes", TRIGGER: "triggers", TOOL: "tools", CONNECTION: "connections"}


class TestViewPanel:
    """Settings → What you see: which boxes, triggers, tools and connections the toolbox offers, by the three
    checks of the test record (TestView). A change counts at once: the next Add box or Add trigger window has it; the menu's
    list of tools after the page is opened again. `items` gives the toolbox's list of things to test, for the
    line that says how many are shown."""

    __test__ = False  # not a test class, whatever its name says to a test runner

    def __init__(self, view: TestView, items: Callable[[], list[TestItem]]) -> None:
        self._view = view
        self._items = items

    @ui.refreshable_method
    def build(self) -> None:
        view = self._view
        ui.label("What you see").classes("text-lg font-semibold")
        ui.label("Which boxes, triggers, tools and connections the toolbox offers. A flow that already uses one "
                 "keeps it and keeps running, a hidden connection stays connected, and your own flows are "
                 "always there. Pages are never hidden.").classes("text-sm opacity-80")
        ui.toggle(MODE_TITLES, value=view.mode, on_change=lambda e: self._set(lambda: view.set_mode(e.value))) \
            .props("no-caps unelevated")
        ui.label(MODE_HELP[view.mode]).classes("text-sm opacity-80")
        if view.mode == TESTED:
            with ui.row().classes("items-center gap-4"):
                for check, title in CHECKS.items():
                    ui.checkbox(title, value=check in view.needed,
                                on_change=lambda e, c=check: self._set(lambda: view.need(c, e.value)))
            if not view.needed:
                ui.label("No check picked: that shows everything.").classes("text-xs opacity-70")
        shown = view.shown(self._items())
        ui.label("Shown now: " + " · ".join(f"{count} of {of} {KIND_WORDS[kind]}"
                                            for kind, (count, of) in shown.items())).classes("text-sm font-medium")
        ui.label("The checks are ticked in the test window (docs/tested) and read when the toolbox starts.") \
            .classes("text-xs opacity-60")

    def _set(self, change: Callable[[], None]) -> None:
        change()
        self.build.refresh()
