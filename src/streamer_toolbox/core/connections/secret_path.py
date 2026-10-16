import os
import stat
from pathlib import Path
from typing import Any

from streamer_toolbox.core.security.secret_vault import SecretVault


class SecretPath(Path):
    """The path of a file in the secrets folder. It is a Path like any other, but what is read from it and
    written to it goes through the SecretVault: encrypted on disk while a login is set, plain otherwise. So
    the connections keep reading their token file the way they always did (read_text, write_text).

    Only this file itself: its parent, a sibling made with with_name() and the like are plain paths."""

    def __init__(self, *segments: Any, vault: SecretVault) -> None:
        super().__init__(*segments)
        self._vault = vault

    def with_segments(self, *segments: Any) -> Path:
        return Path(*segments)

    def read_bytes(self) -> bytes:
        return self._vault.reveal(Path(self).read_bytes())

    def read_text(self, encoding: str | None = None, errors: str | None = None, newline: str | None = None) -> str:
        text = self.read_bytes().decode(encoding or "utf-8", errors or "strict")
        # like Path.read_text: a file typed on Windows has \r\n line ends
        return text if newline is not None else text.replace("\r\n", "\n").replace("\r", "\n")

    def write_bytes(self, data: bytes) -> int:
        concealed = self._vault.conceal(bytes(data))
        # the folder is the owner's only, also when a connection made it itself before its first token
        # (seen on Linux, 2026-10-12: 755); Windows only knows read-only here, nothing changes there
        folder = Path(self).parent
        folder.mkdir(parents=True, exist_ok=True)
        if os.name == "posix" and stat.S_IMODE(folder.stat().st_mode) != 0o700:
            folder.chmod(0o700)
        Path(self).write_bytes(concealed)
        return len(data)

    def write_text(self, data: str, encoding: str | None = None, errors: str | None = None,
                   newline: str | None = None) -> int:
        self.write_bytes(data.encode(encoding or "utf-8", errors or "strict"))
        return len(data)
