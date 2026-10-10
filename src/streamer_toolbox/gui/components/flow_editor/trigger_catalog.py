from collections.abc import Mapping
from itertools import groupby

from streamer_toolbox.core.actions.registered_action import CATEGORY_TITLES
from streamer_toolbox.core.events.event_fields import EVENT_FIELDS
from streamer_toolbox.gui.components.flow_editor.trigger_entry import TriggerEntry
from streamer_toolbox.gui.components.flow_editor.trigger_kinds import TRIGGER_INFO

TOOLBOX, ANY_PLATFORM = "Toolbox", "Any platform"
FIRST = (TOOLBOX, ANY_PLATFORM)  # on top; the programs follow by name
OWN = ("custom", "timer", "tip")  # nobody's events: the toolbox's own
# an event's first word → its group's name, where the box categories (CATEGORY_TITLES) have none
GROUP_TITLES = {"key": "Keyboard", "youtube": "YouTube", "rumble": "Rumble", "streamelements": "StreamElements",
                "streamlabs": "Streamlabs", "streamsocket": "StreamSocket", "tiltify": "Tiltify",
                "crowdcontrol": "Crowd Control"}


class TriggerCatalog:
    """What the Add trigger window lists: the triggers by group (the toolbox's own, the any-platform ones, then
    each program by name), by title inside a group, and a search over all of them (every word must be somewhere
    in a trigger's title, info, group, name or fields; titles that start with the search come first)."""

    def __init__(self, kinds: Mapping[str, tuple[str, str, str, str]]) -> None:
        entries = [TriggerEntry(kind, icon, title, match, example, group_of(kind), TRIGGER_INFO.get(kind, ""),
                                EVENT_FIELDS.get(kind, ()))
                   for kind, (icon, title, match, example) in kinds.items()]
        self._entries = sorted(entries, key=lambda e: (_group_order(e.group), e.title.casefold()))

    def groups(self) -> list[tuple[str, int]]:
        """(group, number of triggers)."""
        return [(group, len(list(items))) for group, items in groupby(self._entries, key=lambda e: e.group)]

    def entries(self, group: str) -> list[TriggerEntry]:
        return [e for e in self._entries if e.group == group]

    def search(self, text: str) -> list[tuple[str, list[TriggerEntry]]]:
        """(group, the triggers in it that match), groups in the usual order."""
        words = text.casefold().split()
        if not words:
            return []
        hits = [e for e in self._entries if all(w in _haystack(e) for w in words)]
        return [(group, sorted(items, key=lambda e: (not e.title.casefold().startswith(words[0]),
                                                     e.title.casefold())))
                for group, items in groupby(hits, key=lambda e: e.group)]


def group_of(kind: str) -> str:
    """The group a trigger is listed under: the program that tells it, by its first word."""
    if kind in OWN:
        return TOOLBOX
    first, dot, _ = kind.partition(".")
    if not dot and first not in CATEGORY_TITLES:  # chat, follow, ...: CommonEvents
        return ANY_PLATFORM
    return GROUP_TITLES.get(first) or CATEGORY_TITLES.get(first) or first.replace("_", " ").capitalize()


def _haystack(entry: TriggerEntry) -> str:
    return " ".join((entry.title, entry.info, entry.group, entry.kind, *entry.fields)).casefold()


def _group_order(group: str) -> tuple:
    return (FIRST.index(group) if group in FIRST else len(FIRST)), group.casefold()
