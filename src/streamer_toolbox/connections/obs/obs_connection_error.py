class ObsConnectionError(ConnectionError):
    """OBS couldn't be reached or didn't accept the connection (wrong password, websocket server off)."""
