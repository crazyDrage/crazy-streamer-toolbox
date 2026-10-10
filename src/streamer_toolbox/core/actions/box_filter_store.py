import json
from pathlib import Path

from streamer_toolbox.core.actions.box_filter import BoxFilter

# always there, before his own ones
BASIC_FILTERS = (
    BoxFilter("Basics", ("logic", "var", "data", "text", "list", "object", "json", "time", "popup")),
    BoxFilter("Stream programs", ("obs", "vts", "twitch", "mixitup", "sammi", "viewer", "trigger")),
    BoxFilter("Media and files", ("sound", "video", "file", "obs/Media", "obs/Audio", "web", "system")),
    BoxFilter("My flows", ("flow",)),
)


class BoxFilterStore:
    """The filters of the Add box window: the basic ones, then his own from config/box_filters.json (made in
    Settings). Names are unique, ignoring upper/lower case; a basic filter can't be changed or replaced."""

    def __init__(self, path: Path) -> None:
        self._path = path
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        self._custom = [BoxFilter.from_dict(f) for f in data.get("filters", [])]

    def all(self) -> list[BoxFilter]:
        return [*BASIC_FILTERS, *self._custom]

    def custom(self) -> list[BoxFilter]:
        return list(self._custom)

    def get(self, name: str) -> BoxFilter | None:
        return next((f for f in self.all() if f.name.casefold() == str(name).casefold()), None)

    def save(self, box_filter: BoxFilter, old_name: str = "") -> None:
        """Adds it, or replaces the one called old_name (a rename keeps its place in the list)."""
        name = box_filter.name.strip()
        if not name:
            raise ValueError("a filter needs a name")
        if not box_filter.parts:
            raise ValueError("put at least one box in the filter")
        other = self.get(name)
        if other and (other in BASIC_FILTERS or other.name.casefold() != old_name.casefold()):
            raise ValueError(f"there's a filter {other.name!r} already")
        new = BoxFilter(name, box_filter.parts, box_filter.without)
        if any(f.name.casefold() == old_name.casefold() for f in self._custom):
            self._custom = [new if f.name.casefold() == old_name.casefold() else f for f in self._custom]
        else:
            self._custom.append(new)
        self._write()

    def delete(self, name: str) -> None:
        self._custom = [f for f in self._custom if f.name.casefold() != name.casefold()]
        self._write()

    def _write(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps({"filters": [f.to_dict() for f in self._custom]}, indent=2,
                                         ensure_ascii=False), encoding="utf-8")
