from typing import Any

from streamer_toolbox.core.interfaces.box import Box
from streamer_toolbox.core.variables.variable_store import VariableStore



class ViewerBox(Box):
    """What the viewer boxes share (not a box itself: it has no run).

    Values per viewer (e.g. how often someone lurked): one variable holds {viewer: value}. The viewer is
    usually Start's user_login; names are kept in lower case so "VexFan" and "vexfan" are one viewer."""

    def __init__(self, variables: VariableStore) -> None:
        self._variables = variables

    async def names(self) -> list[str]:
        return self._variables.names()

    def _all(self, name: str) -> dict[str, Any]:
        value = self._variables.get(name, {})
        if value in ("", None):
            return {}
        if not isinstance(value, dict):
            raise ValueError(f"variable {name} isn't a per-viewer variable ({value!r})")
        return dict(value)


def _key(user: str) -> str:
    key = str(user).strip().casefold()
    if not key:
        raise ValueError("no viewer: wire Start's user_login into 'user'")
    return key
