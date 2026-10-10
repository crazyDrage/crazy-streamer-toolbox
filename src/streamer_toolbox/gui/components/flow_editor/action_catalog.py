from collections.abc import Callable, Collection
from itertools import groupby

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.box_filter import GENERAL, BoxFilter
from streamer_toolbox.core.actions.registered_action import RegisteredAction

FIRST, LAST = ("logic", "var", "sound", "file"), ("flow",)  # like SAMMI: the basics on top


class ActionCatalog:
    """What the Add box window lists: categories in SAMMI's order (basics first, flows last) with how many boxes
    each has, a category's boxes by sub group, and a search over every box (all words must be somewhere in its
    name, description, category or group; boxes whose name starts with the search come first). With a
    BoxFilter only the boxes that fit it are there at all; `hide` leaves out whole categories (the programs
    that are switched off under Connections); `shows` leaves out single boxes (TestView.shows_box: the ones
    his checks hide)."""

    def __init__(self, actions: ActionRegistry, exclude: str = "", box_filter: BoxFilter | None = None,
                 hide: Collection[str] = (), shows: Callable[[RegisteredAction], bool] | None = None) -> None:
        self._actions = sorted((a for a in actions.all(include_flow_only=True)
                                if a.name != exclude and a.category not in hide
                                and (box_filter is None or box_filter.fits(a))
                                and (shows is None or shows(a))),
                               key=lambda a: (_category_order(a), a.group or GENERAL, a.title.casefold()))

    def count(self) -> int:
        return len(self._actions)

    def categories(self) -> list[tuple[str, str, int]]:
        """(category, its title, number of boxes)."""
        return [(category, items[0].category_title, len(items))
                for category, items in ((c, list(i)) for c, i in groupby(self._actions, key=lambda a: a.category))]

    def groups(self, category: str) -> list[tuple[str, list[RegisteredAction]]]:
        """(sub group, its boxes) of one category; one without sub groups gives one group named ""."""
        in_category = [a for a in self._actions if a.category == category]
        groups = [(group, list(items)) for group, items in groupby(in_category, key=lambda a: a.group or GENERAL)]
        return [("", groups[0][1])] if len(groups) == 1 else groups

    def search(self, text: str) -> list[tuple[str, list[RegisteredAction]]]:
        """(category title, the boxes in it that match), categories in the usual order."""
        words = text.casefold().split()
        if not words:
            return []
        hits = [a for a in self._actions if all(w in _haystack(a) for w in words)]
        found = []
        for _, items in groupby(hits, key=lambda a: a.category):
            items = sorted(items, key=lambda a: (not a.title.casefold().startswith(words[0]),
                                                 a.title.casefold()))
            found.append((items[0].category_title, items))
        return found


def _haystack(action: RegisteredAction) -> str:
    return " ".join((action.title, action.description, action.name, action.category_title,
                     action.group)).casefold()


def _category_order(action: RegisteredAction) -> tuple:
    rank = (FIRST.index(action.category) if action.category in FIRST
            else len(FIRST) + 1 if action.category in LAST else len(FIRST))
    return rank, action.category_title.casefold(), action.category
