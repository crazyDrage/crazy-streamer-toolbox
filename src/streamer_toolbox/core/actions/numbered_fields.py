import re
from collections.abc import Mapping
from typing import Any


def numbered_fields(prefix: str, params: Mapping[str, Any]) -> list[str]:
    """A box's numbered fields, e.g. a Switch's case_1, case_2, ...: as many as the count field says ("cases" = 3)
    or as the highest number found, at least one. Empty ones still count: the editor doesn't save empty fields."""
    found = [int(m.group(1)) for key in params if (m := re.fullmatch(rf"{re.escape(prefix)}_(\d+)", key))]
    try:
        count = int(params.get(count_field(prefix), 0))
    except (TypeError, ValueError):
        count = 0
    return [f"{prefix}_{i}" for i in range(1, max([*found, count, 1]) + 1)]


def count_field(prefix: str) -> str:
    """Where the number of numbered fields is kept: "cases" for "case"."""
    return prefix + "s"
