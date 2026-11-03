from streamer_toolbox.core.variables.boxes.viewer_box import ViewerBox, _key
from streamer_toolbox.core.variables.variable_store import VariableStore


class AddToViewerValue(ViewerBox):
    name = "add"
    label = "Add to viewer value"
    help = "Adds to a viewer's number (starts at 0), e.g. lurks +1; gives back the new number"
    group = "Per viewer"
    flow_only = True

    def __init__(self, variables: VariableStore) -> None:
        super().__init__(variables)
        self.options = {"name": self.names}

    async def run(self, name: str, user: str, amount: float = 1) -> float:
        values = self._all(name)
        try:
            total = float(values.get(_key(user), 0)) + float(amount)
        except (TypeError, ValueError):
            raise ValueError(f"{user}'s value in {name} is not a number ({values.get(_key(user))!r})") from None
        values[_key(user)] = int(total) if total == int(total) else total
        self._variables.set(name, values)
        return values[_key(user)]
