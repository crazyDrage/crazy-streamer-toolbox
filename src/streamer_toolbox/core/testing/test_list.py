import re
from collections.abc import Callable, Iterable
from datetime import date
from pathlib import Path

from streamer_toolbox.core.testing.test_item import BOX, KIND_FOLDERS, PAGE, PAGE_FILE, TestItem

CHECKS = {"works": "Works", "understandable": "Understandable", "usable": "Usable"}
FLAGS = {"works": "is_tested", "understandable": "is_understandable", "usable": "is_usable"}  # on a box
TESTING_FOLDER = Path(__file__).resolve().parents[4] / "docs" / "tested"  # in the project; a build carries it along
HEAD = "| What | Name in the code | AI checked | Works | Understandable | Usable | Last change | Note |"
RULE = "|---|---|---|---|---|---|---|---|"
YES, NO = "yes", "-"
GONE = " (not in the toolbox any more)"
OVERVIEW = "README.md"
INTRO = """# What was tested

The record of what was tried by hand in streamer-toolbox, sorted like the toolbox's side menu, so it can be
gone through one tab after another: one folder per main tab, and in it what is reached from that tab.

- `<tab>/page.md`: the tab's own page and the pages below it in the menu
- `flows/triggers/<program>.md`: the triggers, as the Add trigger window groups them
- `flows/boxes/<category>/<group>.md`: the boxes, as the Add box window sorts them
- `tools/<tool>.md` and `connections/<program>.md`

Every row has three checks. **Works**: it does what it says, on the real program. **Understandable**: its
name, help line and fields tell you what it does. **Usable**: you can set it up and use it without a detour.
A row counts as tested with all three. "Last change" is the day a check of that row was last set or taken back.

**AI checked** comes before those: the day Hex (the AI that builds the toolbox) last tried that thing in the
running toolbox, or `-` when it never did. It is not one of the three checks and opens nothing in a build.
For a page that means: it was opened, it drew and showed no error; not that every button on it was pressed.
For a trigger of a platform or program (Twitch, YouTube, VTube Studio, ...) it means: a stand-in for that
program sent the running toolbox a message in the shape the program documents, the trigger's flow ran and
its Start box got every field. For a connection: its tab drew and showed "connected" to such a stand-in.
The real program was not asked; that is what **Works** is for. A box that talks to a program is only marked
when it was tried on the real program (the example lamp's pretend lamp is its program).

A build of the toolbox carries everything, tested or not. What of it is shown is chosen in Settings → What
you see, which starts on "Tested": only the boxes, triggers and tools with the check Works. (A build made
with `devtools.package tested_only` leaves out what is not tested here.)

Tick the checks in the **test window**, a small window of its own next to the toolbox (it stays open while
the toolbox is restarted, and writes the row's file at once):

    test-window.bat          (Linux: ./test-window.sh)      both are in this folder

To try the boxes without building a flow for each, start the **test toolbox** next to it: a second toolbox on
its own settings folder (`temp/test_settings`) and port 8855, with a flow for every box (Start and that box)
and for every trigger (the trigger and a box that does nothing: when it fires, the flow shows as run).
The flows are numbered in the order of this record ("012 Mute", "T003 Follow"), and the test window shows the
same number on the row.
What you set in a test flow stays when the flows are written again.

    test-toolbox.bat         (Linux: ./test-toolbox.sh)

You can also write `yes` or `-` into a file by hand, and anything into "Note" (not the sign `|`); press
Reload in the test window after that. The toolbox reads the files when it starts.

The files and folders are made by a script of their own, which also adds what is new, moves what was sorted
anew and renews the table below (ticks, days and notes stay):

    $env:PYTHONPATH = "src"; .venv\\Scripts\\python.exe -m streamer_toolbox.devtools.tested
"""


class TestList:
    """What he has tested, kept as text in the project's `docs/tested` folder, sorted like the side menu (the
    files are named by TestInventory: `flows/boxes/obs/scenes.md`, `tools/points.md`, `variables/page.md`):
    one table row per thing with three checks (CHECKS), the day of the last change and a note. Something
    counts as tested only with all three checks. The folder is in git, so it is the proof of what was tried,
    and a build reads it to know what it may offer.

    Read without the toolbox's own list (the test window, a build) it is whole too: every row knows its file.
    take(items) tells it what the toolbox has. sync(items) also writes every file
    anew (devtools/tested does that): a row per thing, so the files also say what is still to test; a row
    whose thing is gone stays, marked as gone, and a file whose rows all moved elsewhere is removed."""

    __test__ = False  # not a test class, whatever its name says to a test runner

    def __init__(self, folder: Path = TESTING_FOLDER, today: Callable[[], date] = date.today) -> None:
        self._folder = folder
        self._today = today
        self._entries: dict[str, dict] = {}  # key → {works, ..., ai_checked, changed, note, title, file}
        self._items: dict[str, TestItem] = {}
        self._headings: dict[Path, str] = {}  # file → its title as read
        for file in sorted(folder.rglob("*.md"), key=self._place(folder)):
            kind = self._kind(file)
            if kind is not None:
                self._read(kind, file)

    def checks(self, key: str) -> dict[str, bool]:
        entry = self._entries.get(key, {})
        return {check: entry.get(check) is True for check in CHECKS}

    def flags(self, key: str) -> dict[str, bool]:
        """The three checks under the names a box has them ({"is_tested": True, ...})."""
        return {FLAGS[check]: done for check, done in self.checks(key).items()}

    def note(self, key: str) -> str:
        return str(self._entries.get(key, {}).get("note", ""))

    def changed(self, key: str) -> str:
        """The day (2026-10-07) a check of it was last set or taken back; "" when never."""
        return str(self._entries.get(key, {}).get("changed", ""))

    def ai_checked(self, key: str) -> str:
        """The day Hex last tried it in the running toolbox; "" when never. Not one of his three checks."""
        return str(self._entries.get(key, {}).get("ai_checked", ""))

    def set_ai_checked(self, key: str, done: bool = True) -> None:
        if key not in self._entries:
            raise KeyError(f"the test record has no row {key!r}")
        self._entries[key]["ai_checked"] = self._today().isoformat() if done else ""
        self._write_for(key)

    def tested(self, key: str) -> bool:
        return all(self.checks(key).values())

    def title(self, key: str) -> str:
        return str(self._entries.get(key, {}).get("title", ""))

    def is_gone(self, key: str) -> bool:
        """True for a row whose thing the toolbox no longer has (it is kept as proof, and counts nowhere)."""
        return key not in self._items if self._items else bool(self._entries.get(key, {}).get("gone"))

    def files(self) -> dict[str, list[str]]:
        """The record's files in the menu's order ("flows/boxes/obs/scenes" → its rows' keys)."""
        files: dict[str, list[str]] = {}
        for key, entry in self._entries.items():
            if "file" in entry:
                files.setdefault(entry["file"].relative_to(self._folder).with_suffix("").as_posix(), []).append(key)
        return files

    def numbers(self, kind: str = BOX) -> dict[str, int]:
        """A running number for every box (or trigger) that is still in the toolbox, in the record's order
        ("box:obs.mute" → 12): what its row in the test window and its flow in the test settings (TestFlows)
        both show. Boxes and triggers are each counted from 1."""
        keys = [key for keys in self.files().values() for key in keys
                if key.startswith(f"{kind}:") and not self.is_gone(key)]
        return {key: number for number, key in enumerate(keys, 1)}

    def heading(self, where: str) -> str:
        """A file's title ("Flows > Boxes > OBS > Scenes")."""
        file = self._folder / f"{where}.md"
        known = [self._items[key].heading for key in self.files().get(where, []) if key in self._items]
        return next((heading for heading in known if heading), self._headings.get(file, file.stem))

    def set_check(self, key: str, check: str, done: bool) -> None:
        if check not in CHECKS:
            raise ValueError(f"check must be one of {', '.join(CHECKS)}, not {check!r}")
        entry = self._entries.setdefault(key, {})
        entry[check] = bool(done)
        entry["changed"] = self._today().isoformat()
        self._write_for(key)

    def set_note(self, key: str, text: str) -> None:
        self._entries.setdefault(key, {})["note"] = _cell(text)
        self._write_for(key)

    def take(self, items: Iterable[TestItem]) -> None:
        """Takes the toolbox's own list: what there is to test and which file each row belongs in. Writes
        nothing."""
        self._items = {item.key: item for item in items}
        # in the toolbox's order (the menu's), then the rows of what is gone
        self._entries = {key: self._entries.get(key, {}) for key in self._items} | {
            key: entry for key, entry in self._entries.items() if key not in self._items}
        for item in self._items.values():
            self._entries[item.key].update(title=item.title, file=self._file(item))

    def sync(self, items: Iterable[TestItem]) -> None:
        """Takes the toolbox's own list and writes every file anew: a row per thing, tested or not."""
        self.take(items)
        files = {entry["file"] for entry in self._entries.values() if "file" in entry}
        for file in files:
            self._write(file)
        for file in set(self._headings) - files:  # every row it had is in another file now
            file.unlink(missing_ok=True)
            for parent in file.relative_to(self._folder).parents[:-1]:
                if not any((self._folder / parent).iterdir()):
                    (self._folder / parent).rmdir()
        self._overview()

    @staticmethod
    def _place(folder: Path) -> Callable[[Path], tuple[int, str]]:
        """Sorts the files as the overview lists them (the menu's order, written by the last sync), so the
        record keeps that order when it is read without the toolbox's own list; new files come after, by name."""
        overview = folder / OVERVIEW
        text = overview.read_text(encoding="utf-8") if overview.is_file() else ""
        order = {where: n for n, where in enumerate(re.findall(r"^\| \[[^\]]+\]\(([^)]+)\.md\)", text, re.M))}
        return lambda file: (order.get(file.relative_to(folder).with_suffix("").as_posix(), len(order)),
                             file.as_posix())

    def _file(self, item: TestItem) -> Path:
        return self._folder / f"{item.file}.md"

    def _kind(self, file: Path) -> str | None:
        """What a file of the record holds, by where it is; None for a file that is not the record's."""
        where = file.relative_to(self._folder).with_suffix("").as_posix()
        if file.stem == PAGE_FILE and "/" in where:
            return PAGE
        return next((kind for kind, start in KIND_FOLDERS.items() if where.startswith(f"{start}/")), None)

    def _write_for(self, key: str) -> None:
        file = self._entries[key].get("file")
        if file is not None:  # a key the toolbox doesn't have and no file names: nowhere to write it
            self._write(file)
            self._overview()

    def _read(self, kind: str, file: Path) -> None:
        lines = file.read_text(encoding="utf-8").splitlines()
        for line in lines:
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            name = re.fullmatch(r"`(.+)`", cells[1]) if len(cells) == 8 else None
            if name is None:
                continue
            checks = {check: cells[3 + i].lower() == YES for i, check in enumerate(CHECKS)}
            self._entries[f"{kind}:{name.group(1)}"] = {
                **checks, "ai_checked": "" if cells[2] == NO else cells[2],
                "changed": "" if cells[6] == NO else cells[6], "note": cells[7],
                "title": cells[0].removesuffix(GONE.strip()).strip(), "file": file,
                "gone": cells[0].endswith(GONE.strip())}
            self._headings[file] = lines[0].removeprefix("# ") if lines[0].startswith("# ") else file.stem

    def _write(self, file: Path) -> None:
        rows = [(key, entry) for key, entry in self._entries.items() if entry.get("file") == file]
        heading = self.heading(file.relative_to(self._folder).with_suffix("").as_posix())
        lines = [f"# {heading}", "", HEAD, RULE]
        for key, entry in rows:
            gone = GONE if self.is_gone(key) else ""
            cells = [entry.get("title", "") + gone, f"`{key.split(':', 1)[1]}`", entry.get("ai_checked") or NO,
                     *(YES if entry.get(check) is True else NO for check in CHECKS),
                     entry.get("changed") or NO, entry.get("note", "")]
            lines.append("| " + " | ".join(cells) + " |")
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")

    def _overview(self) -> None:
        """README.md of the folder: what it is, and how far each file is, in the menu's order."""
        tabs: dict[str, dict[str, list[str]]] = {}  # main tab → file → keys
        for key, entry in self._entries.items():
            if "file" in entry and not self.is_gone(key):
                where = entry["file"].relative_to(self._folder).with_suffix("").as_posix()
                tabs.setdefault(where.split("/")[0], {}).setdefault(where, []).append(key)
        lines = [INTRO, "## How far it is", "", "| Where | Tested | Of |", "|---|---|---|"]
        for tab, files in tabs.items():
            of_tab = [key for keys in files.values() for key in keys]
            lines.append(f"| **[{tab}]({tab}/)** | **{self._done(of_tab)}** | **{len(of_tab)}** |")
            for where, keys in files.items():
                lines.append(f"| [{where}]({where}.md) | {self._done(keys)} | {len(keys)} |")
        total = [key for files in tabs.values() for keys in files.values() for key in keys]
        lines.append(f"| **All** | **{self._done(total)}** | **{len(total)}** |")
        self._folder.mkdir(parents=True, exist_ok=True)
        (self._folder / OVERVIEW).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    def _done(self, keys: Iterable[str]) -> int:
        return len([key for key in keys if self.tested(key)])


def _cell(text: str) -> str:
    """A note as one table cell: one line, without the sign that ends a cell."""
    return " ".join(text.replace("|", "/").split())
