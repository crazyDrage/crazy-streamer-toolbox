import fnmatch
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Caller:
    """Someone allowed to call the HTTP API (SAMMI, Kit, ...) and the actions they may run.

    A caller is recognised by its token, or, with `local = true`, by calling from this PC without one.
    `allow` holds action names or patterns like "hello.*"; "*" allows everything.
    """

    name: str
    allow: tuple[str, ...]
    token: Optional[str] = None
    local: bool = False

    def may_run(self, action_name: str) -> bool:
        return any(fnmatch.fnmatchcase(action_name, pattern) for pattern in self.allow)
