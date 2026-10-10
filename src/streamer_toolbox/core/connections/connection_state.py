from enum import Enum


class ConnectionState(Enum):
    OFF = "off"                # switched off in the settings
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"            # switched on, but the last try failed
