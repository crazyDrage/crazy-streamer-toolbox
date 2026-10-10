class NotConnectedError(ConnectionError):
    """An action needed a connection that is off or failed; the message says which and why."""
