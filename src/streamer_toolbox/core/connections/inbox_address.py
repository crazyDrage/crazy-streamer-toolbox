from urllib.parse import quote

DEFAULT_TYPE = "default"  # his 11-21
HOST = "127.0.0.1"  # not localhost: VNyan turns that into ::1, the toolbox listens on IPv4 (his 11-22)


def inbox_address(port: int, connection_id: str, kind: str, key: str) -> str:
    """The address a program connects to so its messages of this type come in (MessageInbox)."""
    return (f"ws://{HOST}:{port}/connections/{connection_id}/in/"
            f"{quote(kind.strip() or DEFAULT_TYPE, safe='')}?key={key}")
