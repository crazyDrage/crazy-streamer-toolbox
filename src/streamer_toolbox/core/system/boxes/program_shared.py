import shlex
from typing import Any


def _arguments(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if value is None or value == "":
        return []
    return [part[1:-1] if len(part) > 1 and part[0] == part[-1] == '"' else part
            for part in shlex.split(str(value), posix=False)]


def _text(data: bytes | None) -> str:
    return (data or b"").decode("utf-8", errors="replace")
