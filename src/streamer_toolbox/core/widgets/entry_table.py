import copy
from typing import Any

# what a cell can hold (a picture or video: a file of the widget, or an address with the event's values)
CELL_KINDS = {"text": "Text", "image": "Picture or GIF", "video": "Video"}
SIDES = ("top", "right", "bottom", "left")
# a side → the step it is: (columns, rows)
STEP = {"top": (0, -1), "right": (1, 0), "bottom": (0, 1), "left": (-1, 0)}
# what a cell holds (moves with it); where it is stays
CONTENT = ("kind", "text", "file", "address", "style", "emoji_dict", "emoji_size")
PICTURE = "{picture}"  # what the first lists' own "picture" cell showed: a flow can give that value
# his round 90: a picture or video behind the whole entry and one in front of it (a glass, a frame)
LAYERS = {"back": "Behind", "front": "In front"}
LAYER_KINDS = {"image": "Picture or GIF", "video": "Video"}
# how a layer's picture fills the entry
FITS = {"cover": "Fill (cut to fit)", "fill": "Stretch", "contain": "Whole picture", "repeat": "Repeat"}


class EntryTable:
    """How one event looks in an event list (the widget editor's "Event list" piece; his round 89): a grid of
    columns and rows, like a table in a word processor. A cell sits on one or more spots of it (it spans
    columns and rows); a spot can also stay empty. Cells never lie on top of each other: every change keeps it
    so, and a broken table (an older one) is put right when it is read.

    Each cell holds a text (with the event's values by their names, {user}), a picture or GIF, or a video: a
    file of the widget's media folder, or an address (a web address, a path on this PC or in the toolbox's
    folder) that may have the event's values in it. element.js /
    event_entry.js draw it as a CSS grid.

    What he can do (his check, 2026-11-13: "left/right should move to a different column, up/down to a
    different row", "moving should never spawn an item", removing must always work):
    - add: a new cell beside the cell: on the empty spots there, else in a new column or row
    - move: the cell goes one column or row along; what was there takes its old place, or (when it is bigger)
      gets smaller
    - join: the cell grows over the next column or row on that side; what was there goes or gets smaller
    - put: a new cell on an empty spot
    - remove: the cell goes, its spots are empty

    Behind and in front of the whole entry it can have a layer (his round 90: a picture as every event's
    background, a glass in front): a picture or video like a cell's, that covers the entry (`fit`, FITS) and
    can be see-through (`opacity`).

    A text cell can show words as pictures (his 2026-11-16): `emoji_dict` names the event's value that holds an
    emoji dictionary, {"Kappa": a picture's address} (Twitch emotes gives one); `emoji_size` is their height in
    pixels (0: as high as the words).

    Plain data, kept in the piece's settings: {"columns", "rows", "cells": [{"col", "row", "cols", "rows",
    "kind", "text", "file", "address", "style", "emoji_dict", "emoji_size"}], "style": the look of the whole entry, "layers": {"back",
    "front": {"kind", "file", "address", "fit", "opacity"}} (only the ones it has)}."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data

    @classmethod
    def new(cls, text: str = "{user}") -> "EntryTable":
        return cls({"columns": 1, "rows": 1, "cells": [_cell(0, 0, "text", text)],
                    "style": {"backgroundColor": "rgba(0, 0, 0, 0.6)", "borderRadius": "12px",
                              "padding": "8px 14px", "color": "#ffffff", "fontFamily": "Arial",
                              "fontSize": "28px"}})

    @classmethod
    def of(cls, data: Any) -> "EntryTable":
        """A table from saved settings; what can't be one (missing, broken) is a new one. Cells that lie on top
        of others (a table of the first event list could get them) get smaller: the ones that hold something
        keep their place first."""
        if not isinstance(data, dict) or not isinstance(data.get("cells"), list):
            return cls.new()
        table = cls(copy.deepcopy(data))
        cells = []
        for cell in table.data["cells"]:
            if not isinstance(cell, dict):
                continue
            for key in ("text", "file", "address", "emoji_dict"):
                cell.setdefault(key, "")
            cell.setdefault("style", {})
            cell["emoji_size"] = _size(cell.get("emoji_size"))
            if cell.get("kind") == "picture":  # the first event list's own kind: now a picture with that value
                cell.update(kind="image", address=PICTURE)
            if cell.get("kind") not in CELL_KINDS:
                cell["kind"] = "text"
            try:
                cell.update(col=max(int(cell["col"]), 0), row=max(int(cell["row"]), 0),
                            cols=max(int(cell["cols"]), 1), rows=max(int(cell["rows"]), 1))
            except (KeyError, TypeError, ValueError):
                continue
            cells.append(cell)
        if not cells:
            return cls.new()
        layers = table.data.get("layers")
        table.data["layers"] = {side: _layer(layers[side]) for side in LAYERS
                                if isinstance(layers, dict) and isinstance(layers.get(side), dict)
                                and layers[side].get("kind") in LAYER_KINDS}
        if not table.data["layers"]:
            table.data.pop("layers")
        kept: list[dict[str, Any]] = []
        for cell in sorted(cells, key=lambda each: not _holds_something(each)):
            if all(not _overlap(cell, other) or _cut(cell, other) for other in kept):
                kept.append(cell)
        table.data["cells"] = [cell for cell in cells if any(cell is each for each in kept)]
        table._tidy()
        return table

    def cells(self) -> list[dict[str, Any]]:
        return self.data["cells"]

    def cell(self, number: int) -> dict[str, Any]:
        if not 0 <= number < len(self.cells()):
            raise KeyError(f"no cell {number}")
        return self.cells()[number]

    def empty_spots(self) -> list[tuple[int, int]]:
        """The spots no cell is on, (col, row)."""
        taken = {(col, row) for cell in self.cells() for col in range(cell["col"], cell["col"] + cell["cols"])
                 for row in range(cell["row"], cell["row"] + cell["rows"])}
        return [(col, row) for row in range(self.data["rows"]) for col in range(self.data["columns"])
                if (col, row) not in taken]

    def add(self, number: int, side: str) -> int:
        """A new, empty text cell beside the cell (as high or as wide as it is); the number of the new cell.
        It goes on the spots there when they are empty, else into a new column (left, right) or row (top,
        bottom) right next to the cell: the cells that line goes through get bigger, the others' spots in it
        stay empty."""
        cell = self.cell(number)
        across = _across(side)
        start, span = ("col", "cols") if across else ("row", "rows")
        dx, dy = STEP[side]
        beside = {"col": cell["col"] + (cell["cols"] if dx > 0 else dx), "cols": 1 if across else cell["cols"],
                  "row": cell["row"] + (cell["rows"] if dy > 0 else dy), "rows": cell["rows"] if across else 1}
        empty = set(self.empty_spots())
        if all((col, row) in empty for col in range(beside["col"], beside["col"] + beside["cols"])
               for row in range(beside["row"], beside["row"] + beside["rows"])):
            new = _cell(0, 0, "text", "")
            new.update(beside)
            self.cells().append(new)
            return len(self.cells()) - 1
        line = cell[start] + cell[span] if side in ("right", "bottom") else cell[start]
        self._insert(across, line)
        new = _cell(cell["col"], cell["row"], "text", "")
        new.update(cols=cell["cols"], rows=cell["rows"])
        new[start], new[span] = line, 1
        self.cells().append(new)
        return len(self.cells()) - 1

    def move(self, number: int, side: str) -> int:
        """The cell goes one column or row along. A cell that was there fully goes to the cell's old place; one
        that reaches further gets smaller (it keeps its biggest part). Nothing new is made; the cell's number
        stays. ValueError at the edge."""
        cell = self.cell(number)
        dx, dy = STEP[_side(side)]
        if cell["col"] + dx < 0 or cell["row"] + dy < 0 or cell["col"] + cell["cols"] + dx > self.data["columns"] \
                or cell["row"] + cell["rows"] + dy > self.data["rows"]:
            raise ValueError("it is at the edge already")
        target = {"col": cell["col"] + dx, "row": cell["row"] + dy, "cols": cell["cols"], "rows": cell["rows"]}
        for other in self.cells():
            if other is cell or not _overlap(other, target):
                continue
            if _inside(other, target):  # it goes to the place the cell leaves
                other["col"] -= dx * cell["cols"]
                other["row"] -= dy * cell["rows"]
            else:
                _cut(other, target)
        cell.update(col=target["col"], row=target["row"])
        self._tidy()
        return number

    def join(self, number: int, side: str) -> None:
        """The cell grows over the next column or row on that side (it keeps what it holds; when it holds
        nothing, it takes what the first cell there held). A cell that was fully there goes; one that reaches
        further gets smaller. ValueError at the edge."""
        cell = self.cell(number)
        dx, dy = STEP[_side(side)]
        grown = {"col": cell["col"] + min(dx, 0), "row": cell["row"] + min(dy, 0),
                 "cols": cell["cols"] + abs(dx), "rows": cell["rows"] + abs(dy)}
        if grown["col"] < 0 or grown["row"] < 0 or grown["col"] + grown["cols"] > self.data["columns"] \
                or grown["row"] + grown["rows"] > self.data["rows"]:
            raise ValueError("there's nothing on that side")
        gone = []
        for other in self.cells():
            if other is cell or not _overlap(other, grown):
                continue
            if _inside(other, grown):
                gone.append(other)
            else:
                _cut(other, grown)
        if gone and not _holds_something(cell):
            for key in CONTENT:
                cell[key] = copy.deepcopy(gone[0][key])
        cell.update(grown)
        self.data["cells"] = [each for each in self.cells() if not any(each is other for other in gone)]
        self._tidy()

    def put(self, col: int, row: int) -> int:
        """A new, empty text cell on that empty spot; its number."""
        if (col, row) not in self.empty_spots():
            raise ValueError("there's a cell there already")
        self.cells().append(_cell(col, row, "text", ""))
        return len(self.cells()) - 1

    def remove(self, number: int) -> None:
        """Takes the cell away; its spots are empty (a column or row that is empty all along goes). ValueError
        only for the last cell."""
        self.cell(number)
        if len(self.cells()) == 1:
            raise ValueError("an entry keeps one cell at least")
        del self.cells()[number]
        self._tidy()

    def set_cell(self, number: int, **changes: Any) -> None:
        """kind (CELL_KINDS), text, file, address, emoji_dict (the name of the event's value with the emoji
        dictionary, "" for none), emoji_size (pixels, 0: as high as the words)."""
        cell = self.cell(number)
        if "kind" in changes and changes["kind"] not in CELL_KINDS:
            raise ValueError(f"a cell can't hold {changes['kind']!r}")
        for key in ("kind", "text", "file", "address", "emoji_dict"):
            if key in changes:
                cell[key] = str(changes[key] or "")
        if "emoji_size" in changes:
            cell["emoji_size"] = _size(changes["emoji_size"])

    def set_style(self, number: int | None, **style: Any) -> None:
        """CSS of a cell, or (None) of the whole entry; None or "" takes it away."""
        own = self.data.setdefault("style", {}) if number is None else self.cell(number).setdefault("style", {})
        for key, value in style.items():
            if value is None or value == "":
                own.pop(key, None)
            else:
                own[key] = value

    def layer(self, side: str) -> dict[str, Any] | None:
        """The layer behind ("back") or in front ("front") of the whole entry: {kind, file, address, fit,
        opacity}; None when it has none."""
        if side not in LAYERS:
            raise ValueError(f"not a layer: {side!r}")
        found = (self.data.get("layers") or {}).get(side)
        return dict(found) if found else None

    def set_layer(self, side: str, **changes: Any) -> None:
        """kind (LAYER_KINDS, or "" for no layer there), file, address, fit (FITS), opacity (0 to 1)."""
        now = self.layer(side) or _layer({})
        if "kind" in changes and not changes["kind"]:
            layers = self.data.get("layers") or {}
            layers.pop(side, None)
            if not layers:
                self.data.pop("layers", None)
            return
        if changes.get("kind", now["kind"]) not in LAYER_KINDS:
            raise ValueError(f"a layer can't hold {changes['kind']!r}")
        if "fit" in changes and changes["fit"] not in FITS:
            raise ValueError(f"not a fit: {changes['fit']!r}")
        self.data.setdefault("layers", {})[side] = _layer({**now, **changes})

    def files(self) -> set[str]:
        """The files of the widget's media folder its cells and layers use."""
        return {own["file"] for own in [*self.cells(), *(self.data.get("layers") or {}).values()]
                if own.get("file") and "/" not in own["file"]}

    def addresses(self) -> set[str]:
        """The addresses its picture and video cells and its layers have (with the event's values in them)."""
        return {own["address"].strip() for own in [*self.cells(), *(self.data.get("layers") or {}).values()]
                if own.get("kind") in ("image", "video") and str(own.get("address") or "").strip()}

    def _insert(self, across: bool, line: int) -> None:
        """An empty column (across) or row at that line; the cells it goes through get bigger."""
        start, span, size = ("col", "cols", "columns") if across else ("row", "rows", "rows")
        for each in self.cells():
            if each[start] >= line:
                each[start] += 1
            elif each[start] + each[span] > line:
                each[span] += 1
        self.data[size] += 1

    def _tidy(self) -> None:
        """Columns and rows no cell is on go, and so do the lines between two columns (rows) no cell starts or
        ends at; the table is as big as its cells reach."""
        for start, span, size in (("col", "cols", "columns"), ("row", "rows", "rows")):
            used = sorted({line for cell in self.cells() for line in range(cell[start], cell[start] + cell[span])})
            place = {line: number for number, line in enumerate(used)}
            for cell in self.cells():  # the empty lines out (a cell is on lines that follow one another)
                cell[start] = place[cell[start]]
            edges = sorted({0, *(c[start] for c in self.cells()), *(c[start] + c[span] for c in self.cells())})
            place = {line: number for number, line in enumerate(edges)}
            for cell in self.cells():
                end = place[cell[start] + cell[span]]
                cell[start] = place[cell[start]]
                cell[span] = end - cell[start]
            self.data[size] = len(edges) - 1


def _cell(col: int, row: int, kind: str, text: str) -> dict[str, Any]:
    return {"col": col, "row": row, "cols": 1, "rows": 1, "kind": kind, "text": text, "file": "", "address": "",
            "style": {}, "emoji_dict": "", "emoji_size": 0}


def _size(found: Any) -> int:
    """An emoji's height in pixels: 0 (as high as the words) for nothing or anything else."""
    try:
        return max(0, min(int(float(found or 0)), 500))
    except (TypeError, ValueError):
        return 0


def _layer(found: dict[str, Any]) -> dict[str, Any]:
    """A layer's settings, put right."""
    try:
        opacity = max(0.0, min(float(found.get("opacity", 1)), 1.0))
    except (TypeError, ValueError):
        opacity = 1.0
    return {"kind": found.get("kind") if found.get("kind") in LAYER_KINDS else "image",
            "file": str(found.get("file") or ""), "address": str(found.get("address") or ""),
            "fit": found.get("fit") if found.get("fit") in FITS else "cover", "opacity": opacity}


def _side(side: str) -> str:
    if side not in SIDES:
        raise ValueError(f"not a side: {side!r}")
    return side


def _across(side: str) -> bool:
    return _side(side) in ("left", "right")


def _holds_something(cell: dict[str, Any]) -> bool:
    return bool(str(cell.get("text") or "").strip() or cell.get("file") or str(cell.get("address") or "").strip())


def _overlap(cell: dict[str, Any], other: dict[str, Any]) -> bool:
    return cell["col"] < other["col"] + other["cols"] and other["col"] < cell["col"] + cell["cols"] \
        and cell["row"] < other["row"] + other["rows"] and other["row"] < cell["row"] + cell["rows"]


def _inside(cell: dict[str, Any], area: dict[str, Any]) -> bool:
    return area["col"] <= cell["col"] and cell["col"] + cell["cols"] <= area["col"] + area["cols"] \
        and area["row"] <= cell["row"] and cell["row"] + cell["rows"] <= area["row"] + area["rows"]


def _cut(cell: dict[str, Any], area: dict[str, Any]) -> bool:
    """The cell keeps its biggest part outside the area (a cell is a rectangle); False when nothing is left."""
    left, top = cell["col"], cell["row"]
    right, bottom = left + cell["cols"], top + cell["rows"]
    parts = [(left, top, min(right, area["col"]), bottom),
             (max(left, area["col"] + area["cols"]), top, right, bottom),
             (left, top, right, min(bottom, area["row"])),
             (left, max(top, area["row"] + area["rows"]), right, bottom)]
    parts = [part for part in parts if part[2] > part[0] and part[3] > part[1]]
    if not parts:
        return False
    best = max(parts, key=lambda part: (part[2] - part[0]) * (part[3] - part[1]))
    cell.update(col=best[0], row=best[1], cols=best[2] - best[0], rows=best[3] - best[1])
    return True
