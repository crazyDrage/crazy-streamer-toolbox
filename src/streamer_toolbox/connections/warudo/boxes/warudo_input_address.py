from collections.abc import Callable

from streamer_toolbox.core.connections.inbox_address import DEFAULT_TYPE
from streamer_toolbox.core.interfaces.box import Box


class WarudoInputAddress(Box):
    """The address Warudo's "Send Websocket Asset" connects to, with its key, for one type (his 11-21): wired
    into "Send action to Warudo" it lets a Warudo blueprint set the asset's URL, so it connects again after
    the toolbox was closed. The key comes from the toolbox, never typed into a box (rule 36)."""

    name = "input_address"
    label = "Warudo input address"
    help = "The address (with its key) Warudo connects to so its messages of this type come in"
    hints = {"type": "The type at the end of the address; listed under Connections → Warudo once it connected"}
    data_only = True  # no run wire: the toolbox's own value (rule 22)

    def __init__(self, address: Callable[[str], str], known: Callable[[], list[str]]) -> None:
        self._address = address

        async def types() -> list[str]:
            return known() or [DEFAULT_TYPE]

        self.options = {"type": types}  # the types that connected once; typing another works too

    async def run(self, type: str = DEFAULT_TYPE) -> str:
        return self._address(str(type))
