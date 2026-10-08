from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.variables.variable_store import VariableStore


class ViewerActions:
    """Values per viewer (e.g. how often someone lurked): one variable holds {viewer: value}. The viewer is
    usually Start's user_login; names are kept in lower case so "VexFan" and "vexfan" are one viewer."""

    def __init__(self, variables: VariableStore) -> None:
        self._variables = variables

    def add_to(self, actions: ActionRegistry) -> None:
        async def names() -> list[str]:
            return self._variables.names()

        actions.add("viewer.get", self.get, "A viewer's value in a per-viewer variable (default if they have none "
                    "yet)", "Get viewer value", group="Per viewer", options={"name": names}, flow_only=True,
                    typed=("default",))
        actions.add("viewer.set", self.set, "Sets a viewer's value in a per-viewer variable", "Set viewer value",
                    group="Per viewer", options={"name": names}, flow_only=True, typed=("value",))
        actions.add("viewer.add", self.add, "Adds to a viewer's number (starts at 0), e.g. lurks +1; gives back "
                    "the new number", "Add to viewer value", group="Per viewer", options={"name": names},
                    flow_only=True)
        actions.add("viewer.top", self.top, "The viewers with the highest numbers, as a list of {user, value}",
                    "Top viewers", group="Per viewer", options={"name": names}, flow_only=True)

    async def get(self, name: str, user: str, default: Any = "") -> Any:
        return self._all(name).get(_key(user), default)

    async def set(self, name: str, user: str, value: Any = "") -> Any:
        values = self._all(name)
        values[_key(user)] = value
        self._variables.set(name, values)
        return value

    async def add(self, name: str, user: str, amount: float = 1) -> float:
        values = self._all(name)
        try:
            total = float(values.get(_key(user), 0)) + float(amount)
        except (TypeError, ValueError):
            raise ValueError(f"{user}'s value in {name} is not a number ({values.get(_key(user))!r})") from None
        values[_key(user)] = int(total) if total == int(total) else total
        self._variables.set(name, values)
        return values[_key(user)]

    async def top(self, name: str, count: int = 5) -> list[dict[str, Any]]:
        numbers = []
        for user, value in self._all(name).items():
            try:
                numbers.append({"user": user, "value": float(value) if not isinstance(value, int) else value})
            except (TypeError, ValueError):
                continue
        return sorted(numbers, key=lambda n: n["value"], reverse=True)[:max(int(count), 0)]

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
