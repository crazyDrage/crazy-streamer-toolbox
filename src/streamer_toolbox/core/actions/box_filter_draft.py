from collections.abc import Iterable

from streamer_toolbox.core.actions.box_filter import BoxFilter, part_of
from streamer_toolbox.core.actions.registered_action import RegisteredAction


class BoxFilterDraft:
    """A filter while it's being edited: boxes go in and out one by one, or a whole category / sub group at once.
    A whole one stays "whole" (boxes added to it later are in too); a box taken out of it is remembered as
    left out. `boxes` = every box of the category or group that is moved."""

    def __init__(self, box_filter: BoxFilter | None = None) -> None:
        self.parts: list[str] = list(box_filter.parts) if box_filter else []
        self.without: list[str] = list(box_filter.without) if box_filter else []

    def to_filter(self, name: str = "") -> BoxFilter:
        return BoxFilter(name, tuple(self.parts), tuple(self.without))

    def has(self, action: RegisteredAction) -> bool:
        return self.to_filter().fits(action)

    def whole(self, part: str) -> bool:
        """True if that category ("obs") or sub group ("obs/Media") is in as a whole."""
        return part in self.parts or part.split("/", 1)[0] in self.parts

    def add(self, action: RegisteredAction) -> None:
        _drop(self.without, action.name)
        if not self.has(action):
            self.parts.append(action.name)

    def remove(self, action: RegisteredAction) -> None:
        _drop(self.parts, action.name)
        if self.has(action):  # in through its category or group
            self.without.append(action.name)

    def add_all(self, part: str, boxes: Iterable[RegisteredAction]) -> None:
        """The whole category or sub group; its single boxes and (for a category) its groups merge into it."""
        boxes = list(boxes)
        for action in boxes:
            _drop(self.parts, action.name)
            _drop(self.without, action.name)
            if "/" not in part:
                _drop(self.parts, part_of(action))
        if not self.whole(part):
            self.parts.append(part)

    def remove_all(self, part: str, boxes: Iterable[RegisteredAction]) -> None:
        """Every box of the category or sub group goes out (a group out of a whole category: each is left out)."""
        boxes = list(boxes)
        _drop(self.parts, part)
        for action in boxes:
            if "/" not in part:
                _drop(self.parts, part_of(action))
            self.remove(action)
        if "/" not in part:  # nothing of the category is left: no need to remember what was left out
            self.without = [name for name in self.without if name not in {a.name for a in boxes}]


def _drop(items: list[str], item: str) -> None:
    while item in items:
        items.remove(item)
