from dataclasses import dataclass, field

from streamer_toolbox.core.connections.connection_state import ConnectionState


@dataclass(frozen=True)
class ConnectionStatus:
    """What the GUI shows for a connection: its state, one line of detail, and a few facts (version, profile...)."""

    state: ConnectionState
    detail: str = ""
    facts: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return self.state is ConnectionState.CONNECTED
