import re
from typing import Any

from streamer_toolbox.core.flows.box_wire import WIRE_IN, box_ref, box_source


class WireMatcher:
    """"Wire by name": pairs a box's fields with other boxes' orange outputs that have the same name (upper/lower
    case, _ and spaces ignored), e.g. Split's width → Set source size's width, Start's scene → every scene. Like
    AVL Model.CONNECT's connection wizard, in its simplest form (same name)."""

    @staticmethod
    def key(name: str) -> str:
        return re.sub(r"[\s_\-]", "", name).casefold()

    @classmethod
    def candidates(cls, fields: list[str], sources: dict[str, str],
                   current: dict[str, Any]) -> list[tuple[str, dict[str, str], str | None]]:
        """Per field that has a same-named output somewhere: (field, {${box...}: label}, the one to tick or None).
        Ticked when the field is still empty or waits for a wire and exactly one output fits; a field that is
        already wired to one of them keeps that one."""
        by_key: dict[str, dict[str, str]] = {}
        for ref, label in sources.items():
            source = box_source(ref)
            if source and source[1]:
                by_key.setdefault(cls.key(source[1].rsplit(".", 1)[-1]), {})[ref] = label
        result = []
        for field in fields:
            matches = by_key.get(cls.key(field))
            if not matches:
                continue
            value = current.get(field, "")
            if value in matches:
                pick = value
            elif value in ("", None, WIRE_IN) and len(matches) == 1:
                pick = next(iter(matches))
            else:
                pick = None
            result.append((field, matches, pick))
        return result

    @classmethod
    def by_name(cls, fields: list[str], source: str, outputs: list[str],
                current: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
        """A result wire dropped on a box's "by name" dot: each field named like one of the result's keys takes
        that key (${box.<source>.<key>}), if it's still empty or waits for a wire. Gives (chosen, kept): kept =
        fields that already have a value or another wire, left alone (field → its value)."""
        keys = {cls.key(name): name for name in outputs}
        chosen, kept = {}, {}
        for field in fields:
            name = keys.get(cls.key(field))
            if name is None:
                continue
            value = current.get(field, "")
            ref = box_ref(source, name)
            if value in ("", None, WIRE_IN) or value == ref:
                chosen[field] = ref
            else:
                kept[field] = value
        return chosen, kept

    @staticmethod
    def as_value(fields: list[str], source: str, output: str, current: dict[str, Any]) -> dict[str, str]:
        """No field is named like the result's keys (an If box: Value / Check / Compare with): the dropped output
        goes into the first field that is still empty or waits for a wire, as its value. {} if none is free."""
        free = next((f for f in fields if current.get(f, "") in ("", None, WIRE_IN)), None)
        return {free: box_ref(source, output)} if free else {}
