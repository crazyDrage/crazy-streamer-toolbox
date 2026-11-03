from collections.abc import Collection
from dataclasses import replace
from pathlib import Path

from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_pack import FlowPack


class DefaultFlows:
    """Ready-made flows put in by a button (his round 66: "a button on every connection with `Add default flows`";
    the Learn tab's "Add to my flows"). They come in switched off, so nothing happens on stream that he didn't
    switch on, in the folder the file names. Pressing again brings back only the ones missing from that folder:
    one he deleted comes back, one he changed stays as it is. A connection's button shows them first and he
    picks which (round 76)."""

    def __init__(self, library: FlowLibrary) -> None:
        self._library = library

    def there(self, file: Path, folder: str = "") -> set[str]:
        """The labels of the file's flows that are in the folder already (casefolded)."""
        folder = folder or FlowPack.from_text(file.read_text(encoding="utf-8")).folder
        return {f.label.casefold() for f in self._library.all() if f.folder == folder}

    def add(self, file: Path, folder: str = "",
            only: Collection[str] | None = None) -> tuple[list[str], list[str]]:
        """Puts the file's flows into folder (default: the file's own); with only, just the flows with those
        labels. Gives the labels added and the labels that were there already."""
        pack = FlowPack.from_text(file.read_text(encoding="utf-8"))
        folder = folder or pack.folder
        have = self.there(file, folder)
        flows = pack.flows if only is None else tuple(f for f in pack.flows if f.label in only)
        missing = tuple(replace(f, enabled=False, folder=folder) for f in flows if f.label.casefold() not in have)
        added = self._library.import_pack(FlowPack(folder, missing), as_is=True) if missing else []
        return [f.label for f in added], [f.label for f in flows if f.label.casefold() in have]
