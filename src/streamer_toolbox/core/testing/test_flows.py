import json
import re
import tomllib
from dataclasses import replace
from pathlib import Path

from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.flows.flow_wire import START, FlowWire
from streamer_toolbox.core.testing.test_inventory import STEP, slug
from streamer_toolbox.core.testing.test_item import BOX
from streamer_toolbox.core.testing.test_list import TestList

MADE = re.compile(r"t(\d{3})_(.+)")  # a test flow's file name: t012_obs_mute


class TestFlows:
    """A flow for every box that has to be tested, written into a settings folder's flows: Start and that one
    box, so testing a box is opening its flow, filling the fields and pressing Test run instead of building a
    flow each time. They are numbered in the record's order (TestList.numbers: "012 Mute", file
    t012_obs_mute.toml; the test window shows the same number on the box's row) and sorted into one folder
    per file of the record ("03 OBS > Audio"). Triggers get no flow: he sets them up by hand (round 51).

    Writing again keeps what he set in a flow: a flow that is there already only gets its number, title and
    folder anew (new boxes move the numbers), and is never emptied. Flows of what is gone stay. A flow he
    deleted stays deleted (his "yes", round 51): `written` (a JSON file) lists every box a flow was ever
    written for, and a box in it whose flow is missing gets none again. Deleting that file brings them back."""

    __test__ = False  # not a test class, whatever its name says to a test runner

    def __init__(self, record: TestList, store: FlowStore, written: Path) -> None:
        self._record = record
        self._store = store
        self._written = written

    def write(self) -> tuple[int, int, int]:
        """Writes the flows; gives (how many are new, how many were there already, how many he deleted)."""
        there = {made.group(2): path for path in self._store.folder.glob("t*.toml")
                 if (made := MADE.fullmatch(path.stem))}
        written = self._read_written()
        folders = self._folders()
        new = total = deleted = 0
        for key, number in self._record.numbers(BOX).items():
            code = key.split(":", 1)[1]
            name, label = f"t{number:03d}_{slug(code)}", f"{number:03d} {self._record.title(key)}"
            old = there.get(slug(code))
            if old is None and code in written:
                deleted += 1
                continue
            total += 1
            written.add(code)
            if old is None:
                new += 1
                flow = Flow(name, label, (FlowNode("n1", code),), (FlowWire(START, "out", "n1"),),
                            description=f"Test flow for the box {self._record.title(key)} ({code}).",
                            folder=folders[key])
            else:
                kept = FlowStore.parse(old.stem, tomllib.loads(old.read_text(encoding="utf-8")))
                flow = replace(kept, name=name, label=label, folder=folders[key])
                if flow == kept:
                    continue
                old.unlink()
            self._store.save(flow)
        self._written.parent.mkdir(parents=True, exist_ok=True)
        self._written.write_text(json.dumps(sorted(written), indent=1), encoding="utf-8")
        return new, total - new, deleted

    def _read_written(self) -> set[str]:
        try:
            return set(json.loads(self._written.read_text(encoding="utf-8")))
        except (OSError, ValueError):  # none yet (or broken): every box gets its flow once more
            return set()

    def _folders(self) -> dict[str, str]:
        """Each one's folder on the Flows page: its file of the record, numbered ("03 OBS > Audio")."""
        numbers = self._record.numbers(BOX)
        folders: dict[str, str] = {}
        files = [(where, keys) for where, keys in self._record.files().items() if any(k in numbers for k in keys)]
        for count, (where, keys) in enumerate(files, 1):
            title = self._record.heading(where).split(STEP, 2)[-1]  # without "Flows > Boxes > "
            folders.update({key: f"{count:02d} {title}" for key in keys})
        return folders
