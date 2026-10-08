from nicegui import Client


class OpenPages:
    """Every toolbox page open right now (PC, phone, tablet), so a question or a message reaches whatever screen
    the streamer has open."""

    def __init__(self) -> None:
        self._clients: set[Client] = set()

    def attach(self, client: Client) -> None:
        """Called by every page."""
        self._clients.add(client)
        client.on_delete(lambda: self._clients.discard(client))

    def clients(self) -> list[Client]:
        return list(self._clients)
