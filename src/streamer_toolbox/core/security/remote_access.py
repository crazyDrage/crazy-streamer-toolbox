import socket
from typing import Any

from streamer_toolbox.core.config.config_table_writer import ConfigTableWriter
from streamer_toolbox.core.security.password_hash import PasswordHash

LOOPBACK = {"127.0.0.1", "::1", "localhost"}
EVERYWHERE = "0.0.0.0"


class RemoteAccess:
    """Who may open the toolbox's pages. This PC always may, without a password. Other devices on the network
    only when [api] host is 0.0.0.0 (applies after a restart) and only after signing in with the password in
    [access] password_hash. A device's sign-in holds until the password changes."""

    def __init__(self, api_table: dict[str, Any], access_table: dict[str, Any], writer: ConfigTableWriter) -> None:
        self._running_open = api_table.get("host", "127.0.0.1") == EVERYWHERE
        self._open = self._running_open
        self._hash = str(access_table.get("password_hash", ""))
        self._writer = writer

    @staticmethod
    def is_this_pc(address: str | None) -> bool:
        return address in LOOPBACK

    @property
    def has_password(self) -> bool:
        return bool(self._hash)

    @property
    def open(self) -> bool:
        """What's saved: other devices may connect (after a restart, if it just changed)."""
        return self._open

    @property
    def restart_needed(self) -> bool:
        return self._open != self._running_open

    def check(self, password: str) -> bool:
        return self.has_password and PasswordHash.verify(self._hash, password)

    def session_key(self) -> str:
        """Stored with a signed-in device; a new password gives a new key, which signs every device out."""
        return self._hash.rsplit("$", 1)[-1][:24]

    def set_password(self, password: str) -> None:
        self._hash = PasswordHash.make(password)
        self._writer.save("access", {"password_hash": self._hash})

    def set_open(self, open_: bool) -> None:
        if open_ and not self.has_password:
            raise ValueError("set a password first")
        self._open = open_
        self._writer.save("api", {"host": EVERYWHERE if open_ else "127.0.0.1"})

    @staticmethod
    def lan_address() -> str:
        """This PC's address on the home network (what a phone types in). Sends nothing: a UDP socket only picks
        the network card it would use."""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            try:
                s.connect(("10.255.255.255", 1))
                return s.getsockname()[0]
            except OSError:
                return "127.0.0.1"
