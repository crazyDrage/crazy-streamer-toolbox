import re
import tomllib
from collections.abc import Mapping
from dataclasses import replace

from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.flow_wire import START, FlowWire
from streamer_toolbox.core.testing.test_inventory import STEP, slug
from streamer_toolbox.core.testing.test_item import BOX, TRIGGER
from streamer_toolbox.core.testing.test_list import TestList

MADE = re.compile(r"(t|tr)\d{3}_(.+)")  # a test flow's file name: t012_obs_mute (a box), tr003_twitch_follow
START_OF = {BOX: "t", TRIGGER: "tr"}  # how a kind's file names start
SHOWN = {BOX: "", TRIGGER: "T"}  # in front of the number where it is shown ("012 Mute", "T003 Follow")
FIRED = "logic.value"  # the one box of a trigger's flow: does nothing, so the run only shows in the activity


class TestFlows:
    """A flow for every box that has to be tested, written into a settings folder's flows: Start and that one
    box, so testing a box is opening its flow, filling the fields and pressing Test run instead of building a
    flow each time. They are numbered in the record's order (TestList.numbers: "012 Mute", file
    t012_obs_mute.toml; the test window shows the same number on the box's row) and sorted into one folder
    per file of the record ("03 OBS > Audio").

    With `triggers` (kind → (the field it is matched on, the value a new one starts with), the Add trigger
    window's list) every trigger gets a flow too: that trigger as it is when newly added, and one box that
    does nothing, so a run in the activity says the trigger fired ("T003 Follow", tr003_twitch_follow.toml,
    folder "T02 Twitch").

    Writing again keeps what he set in a flow: a flow that is there already only gets its number, title and
    folder anew (new boxes move the numbers), and is never emptied. Flows of what is gone stay."""

    __test__ = False  # not a test class, whatever its name says to a test runner

    def __init__(self, record: TestList, store: FlowStore,
                 triggers: Mapping[str, tuple[str, str]] | None = None) -> None:
        self._record = record
        self._store = store
        self._triggers = dict(triggers or {})

    def write(self) -> tuple[int, int]:
        """Writes the flows; gives (how many are new, how many were there already)."""
        there = {(made.group(1), made.group(2)): path for path in self._store.folder.glob("t*.toml")
                 if (made := MADE.fullmatch(path.stem))}
        new = total = 0
        for kind in (BOX, TRIGGER) if self._triggers else (BOX,):
            folders = self._folders(kind)
            for key, number in self._record.numbers(kind).items():
                code = key.split(":", 1)[1]
                if kind == TRIGGER and code not in self._triggers:
                    continue
                total += 1
                name = f"{START_OF[kind]}{number:03d}_{slug(code)}"
                label = f"{SHOWN[kind]}{number:03d} {self._record.title(key)}"
                old = there.get((START_OF[kind], slug(code)))
                if old is None:
                    new += 1
                    flow = replace(self._fresh(kind, code, self._record.title(key)), name=name, label=label,
                                   folder=folders[key])
                else:
                    kept = FlowStore.parse(old.stem, tomllib.loads(old.read_text(encoding="utf-8")))
                    flow = replace(kept, name=name, label=label, folder=folders[key])
                    if flow == kept:
                        continue
                    old.unlink()
                self._store.save(flow)
        return new, total - new

    def _fresh(self, kind: str, code: str, title: str) -> Flow:
        """A new test flow (its name, label and folder are set by write)."""
        if kind == BOX:
            return Flow("", "", (FlowNode("n1", code),), (FlowWire(START, "out", "n1"),),
                        description=f"Test flow for the box {title} ({code}).")
        field, value = self._triggers[code]
        return Flow("", "", (FlowNode("n1", FIRED, {"value": f"{title} fired"}),), (FlowWire(START, "out", "n1"),),
                    (FlowTrigger(code, {field: value} if field else {}),),
                    f"Test flow for the trigger {title} ({code}): set the trigger up, make it happen, and "
                    "this flow shows as run.")

    def _folders(self, kind: str) -> dict[str, str]:
        """Each one's folder on the Flows page: its file of the record, numbered ("03 OBS > Audio")."""
        numbers = self._record.numbers(kind)
        folders: dict[str, str] = {}
        files = [(where, keys) for where, keys in self._record.files().items() if any(k in numbers for k in keys)]
        for count, (where, keys) in enumerate(files, 1):
            title = self._record.heading(where).split(STEP, 2)[-1]  # without "Flows > Boxes > "
            folders.update({key: f"{SHOWN[kind]}{count:02d} {title}" for key in keys})
        return folders
