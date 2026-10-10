from collections.abc import Callable

from nicegui import ui

from streamer_toolbox.core.testing.test_flows import SHOWN
from streamer_toolbox.core.testing.test_list import CHECKS, TestList

HELP = {"works": "It does what it says, on the real program",
        "understandable": "Its name, help line and fields tell you what it does without asking",
        "usable": "You can set it up and use it without a detour"}
STEP = " > "  # between the steps of a file's heading


class TestWindow:
    """The test window: the test record (docs/tested) as a small page of its own, to keep open next to the
    toolbox while trying things there. It needs no running toolbox and stays open while that is restarted.

    One file of the record at a time, in the menu's order (a main tab's page, a program's triggers, one sub
    group of boxes, ...), with Back / Next to go through them one after another; a search looks through all of
    them. A tick or a note is written into the row's file at once. Reload reads the files again (after the
    files were made anew, or changed by hand)."""

    __test__ = False  # not a test class, whatever its name says to a test runner

    def __init__(self, record: Callable[[], TestList]) -> None:
        self._read = record
        self._tested = record()
        self._where = ""
        self._only_open = False
        self._search = ""

    def build(self) -> None:
        ui.colors(primary="#6d5dfc")
        ui.dark_mode(True)
        with ui.column().classes("w-full max-w-2xl mx-auto p-3 gap-2"):
            with ui.row().classes("items-center w-full no-wrap gap-2"):
                ui.label("Test window").classes("text-lg font-semibold")
                self._summary()
                ui.space()
                ui.button("Reload", icon="refresh", on_click=self._reload).props("flat dense no-caps") \
                    .tooltip("Reads docs/tested again")
            with ui.row().classes("items-center w-full gap-2"):
                ui.switch("Only what is still open", on_change=lambda e: self._set("_only_open", bool(e.value))) \
                    .props("dense")
                ui.input(placeholder="Search everything", on_change=lambda e: self._set(
                    "_search", (e.value or "").strip().casefold())) \
                    .props("dense outlined clearable debounce=200").classes("flex-1 min-w-[10rem]")
            self._body()

    def files(self) -> dict[str, list[str]]:
        """The files that are shown: without the rows of what is gone, and only the open ones if asked."""
        files = {}
        for where, keys in self._tested.files().items():
            keys = [key for key in keys if not self._tested.is_gone(key)
                    and not (self._only_open and self._tested.tested(key))]
            if keys:
                files[where] = keys
        return files

    def found(self) -> dict[str, list[str]]:
        """What the search finds, by file: every word must be in a row's name, code name or its file's title."""
        words = self._search.split()
        found = {}
        for where, keys in self.files().items():
            heading = self._tested.heading(where).casefold()
            hits = [key for key in keys
                    if all(word in f"{self._tested.title(key)} {key} {heading}".casefold() for word in words)]
            if hits:
                found[where] = hits
        return found

    def number(self, key: str) -> str:
        """What a box's or trigger's flow in the test toolbox is numbered ("012", "T003"); "" for the rest."""
        for kind, shown in SHOWN.items():
            if key in self._tested.numbers(kind):
                return f"{shown}{self._tested.numbers(kind)[key]:03d}"
        return ""

    def step(self, by: int) -> None:
        """To the file after (1) or before (-1) the one shown; stays at the ends."""
        names = list(self.files())
        if names:
            here = names.index(self._where) if self._where in names else 0
            self._where = names[max(0, min(len(names) - 1, here + by))]

    def _set(self, name: str, value: object) -> None:
        setattr(self, name, value)
        self._body.refresh()

    def _reload(self) -> None:
        self._tested = self._read()
        self._summary.refresh()
        self._body.refresh()

    def _go(self, by: int) -> None:
        self.step(by)
        self._body.refresh()

    @ui.refreshable_method
    def _summary(self) -> None:
        keys = [key for keys in self._tested.files().values() for key in keys if not self._tested.is_gone(key)]
        done = len([key for key in keys if self._tested.tested(key)])
        ui.label(f"{done} of {len(keys)} tested").classes("text-sm opacity-70")

    @ui.refreshable_method
    def _body(self) -> None:
        if self._search:
            found = self.found()
            if not found:
                ui.label("Nothing matches the search.").classes("opacity-70 p-2")
            for where, keys in found.items():
                ui.label(self._tested.heading(where)).classes("text-sm font-bold text-primary pt-2")
                for key in keys:
                    self._row(key)
            return
        files = self.files()
        if not files:
            ui.label("Nothing here: everything is tested, or docs/tested is empty (make it with "
                     "python -m streamer_toolbox.devtools.tested).").classes("opacity-70 p-2")
            return
        if self._where not in files:
            self._where = next(iter(files))
        names = list(files)
        here = names.index(self._where)
        with ui.row().classes("items-center w-full no-wrap gap-1"):
            ui.button(icon="chevron_left", on_click=lambda: self._go(-1)).props("flat round dense") \
                .tooltip("The one before").set_enabled(here > 0)
            ui.select({where: self._option(where, keys) for where, keys in files.items()}, value=self._where,
                      with_input=True, on_change=lambda e: self._set("_where", e.value)) \
                .props("dense outlined options-dense").classes("flex-1 min-w-0")
            ui.button(icon="chevron_right", on_click=lambda: self._go(1)).props("flat round dense") \
                .tooltip("The next one").set_enabled(here < len(names) - 1)
        ui.label(f"{here + 1} of {len(names)}  ·  docs/tested/{self._where}.md").classes("text-xs opacity-60")
        for key in files[self._where]:
            self._row(key)
        if here < len(names) - 1:
            ui.button(f"Next: {self._tested.heading(names[here + 1])}", icon="chevron_right",
                      on_click=lambda: self._go(1)).props("flat no-caps dense").classes("self-end")

    def _option(self, where: str, keys: list[str]) -> str:
        left = len([key for key in keys if not self._tested.tested(key)])
        return f"{self._tested.heading(where)}  ·  {left} open" if left else f"{self._tested.heading(where)}  ✓"

    def _row(self, key: str) -> None:
        checks = self._tested.checks(key)
        ai_checked = self._tested.ai_checked(key)
        with ui.column().classes("w-full gap-0 border-b border-gray-500/30 py-2"):
            with ui.row().classes("items-baseline w-full gap-2"):
                number = self.number(key)
                if number:
                    ui.label(number).classes("text-xs font-mono text-primary") \
                        .tooltip("The number of its flow in the test toolbox (test-toolbox.bat)")
                ui.label(self._tested.title(key)).classes("font-medium")
                ui.label(key.split(":", 1)[1]).classes("text-xs opacity-60 font-mono")
                ui.space()
                ui.label(f"AI checked {ai_checked}" if ai_checked else "AI: not checked yet") \
                    .classes("text-xs " + ("text-positive" if ai_checked else "opacity-50")) \
                    .tooltip("Whether Hex tried it in the running toolbox before you")
            with ui.row().classes("items-center w-full gap-3"):
                for check, title in CHECKS.items():
                    ui.checkbox(title, value=checks[check],
                                on_change=lambda e, c=check: self._ticked(key, c, e.value)) \
                        .props("dense").tooltip(HELP[check])
            ui.input(placeholder="Note: what was wrong, what to change", value=self._tested.note(key)) \
                .props("dense borderless").classes("w-full") \
                .on("blur", lambda e: self._tested.set_note(key, e.sender.value or ""))

    def _ticked(self, key: str, check: str, done: bool) -> None:
        self._tested.set_check(key, check, done)
        self._summary.refresh()
