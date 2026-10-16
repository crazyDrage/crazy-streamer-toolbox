from collections.abc import Callable

from nicegui import ui

from streamer_toolbox.core.testing.test_item import BOX, CONNECTION, TOOL, TRIGGER, TestItem
from streamer_toolbox.core.testing.test_view import MAY_NOT, NORMAL, TESTING, TestView

MODE_TITLES = {NORMAL: "Normal", TESTING: "Testing"}
MODE_HELP = {NORMAL: "Shows what is done (it has all three checks), and also what you tick below. No tick: only "
                     "what is done. All three ticked: everything.",
             TESTING: "Shows only what you tick below, so you see what is left to do. No tick counts as all "
                      "three. The Debug and the Value box stay, to give the others a value and to read one."}
KIND_WORDS = {BOX: "boxes", TRIGGER: "triggers", TOOL: "tools", CONNECTION: "connections"}


class TestViewPanel:
    """Settings → What you see: which boxes, triggers, tools and connections the toolbox offers: two modes
    (Normal, Testing), a tick for each check of the test record a thing may miss (May not work, ...), and a
    tick for what belongs to a switched-off connection (TestView). A change counts at once: the next Add box or Add trigger window has it; the menu's
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
        with ui.row().classes("items-center gap-4"):
            for check, title in MAY_NOT.items():
                ui.checkbox(title, value=check in view.may_not,
                            on_change=lambda e, c=check: self._set(lambda: view.let_in(c, e.value)))
            ui.checkbox("Disconnected", value=view.disconnected,
                        on_change=lambda e: self._set(lambda: view.set_disconnected(e.value)))
        ui.label("May not work: it has no yes under Works in the test window yet. The other two the same "
                 "way.").classes("text-xs opacity-70")
        ui.label("Disconnected: also the boxes and triggers of a connection that is switched off. Without it "
                 "they are left out of the Add box and the Add trigger window.").classes("text-xs opacity-70")
        shown = view.shown(self._items())
        ui.label("Shown now: " + " · ".join(f"{count} of {of} {KIND_WORDS[kind]}"
                                            for kind, (count, of) in shown.items())).classes("text-sm font-medium")
        ui.label("The checks are ticked in the test window (docs/tested) and read when the toolbox starts.") \
            .classes("text-xs opacity-60")

    def _set(self, change: Callable[[], None]) -> None:
        change()
        self.build.refresh()
