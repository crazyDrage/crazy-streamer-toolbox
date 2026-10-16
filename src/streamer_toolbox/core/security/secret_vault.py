import base64
import json
import logging
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

log = logging.getLogger(__name__)
LOGIN_FILE = "login.json"  # in the secrets folder: the salt and a check value, never the password or the key
MARK = b"toolbox-secret:1:"  # how an encrypted file starts; a file without it is read as it is
CHECK = b"crazy-streamer-toolbox"
MIN_LENGTH = 8
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 15, 8, 1


class SecretVault:
    """The optional login (Settings → Login): with one, every file in the secrets folder is encrypted with a
    key made from the password, and the toolbox can read them only after the password was typed (unlock).
    Without one the files are plain, as before. Nothing outside the secrets folder is touched.

    The password and the key are never written anywhere: login.json holds a random salt and a check value
    that only the right password can open. So a forgotten password can't be recovered; the tokens would have
    to be typed in again. The key lives in memory until the toolbox stops.

    reveal() and conceal() are what SecretPath reads and writes through. A file that is still plain while
    the login is on (written by something else, or left by a switch-on that was cut short) is read as it is
    and encrypted at its next write. While locked, reveal() gives nothing ("no token yet") and conceal()
    refuses, so nothing is ever written plain by mistake."""

    def __init__(self, folder: Path) -> None:
        self._folder = folder
        self._key: Fernet | None = None

    @property
    def active(self) -> bool:
        """Whether a login is set."""
        return (self._folder / LOGIN_FILE).is_file()

    @property
    def unlocked(self) -> bool:
        """Whether the secrets can be read now: no login, or the password was typed."""
        return self._key is not None or not self.active

    def unlock(self, password: str) -> bool:
        """Takes the password after a start; False if it is wrong."""
        key = self._checked(password)
        if key is None:
            return False
        self._key = key
        return True

    def set_login(self, password: str) -> None:
        """Switches the login on and encrypts every file in the folder."""
        if self.active:
            raise ValueError("A login is already set: switch it off first")
        if len(password) < MIN_LENGTH:
            raise ValueError(f"Use at least {MIN_LENGTH} characters")
        salt = os.urandom(16)
        key = _key(password, salt)
        self._folder.mkdir(parents=True, exist_ok=True)
        _replace(self._folder / LOGIN_FILE, json.dumps({
            "salt": base64.b64encode(salt).decode(), "n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P,
            "check": key.encrypt(CHECK).decode()}, indent=1).encode())
        self._key = key
        for file in self._files():
            data = file.read_bytes()
            if not data.startswith(MARK):
                _replace(file, self.conceal(data))

    def remove_login(self, password: str) -> bool:
        """Switches the login off and makes every file plain again; False if the password is wrong."""
        key = self._checked(password)
        if key is None:
            return False
        self._key = key
        for file in self._files():
            data = file.read_bytes()
            if data.startswith(MARK):
                _replace(file, self.reveal(data))
        (self._folder / LOGIN_FILE).unlink(missing_ok=True)
        self._key = None
        return True

    def reveal(self, data: bytes) -> bytes:
        """What a file's bytes say: decrypted when they are encrypted, as they are otherwise."""
        if not data.startswith(MARK):
            return data
        if self._key is None:
            return b""  # locked: like a file that isn't there yet
        try:
            return self._key.decrypt(data[len(MARK):])
        except InvalidToken:
            log.warning("a file in %s can't be opened with this login", self._folder.name)
            return b""

    def conceal(self, data: bytes) -> bytes:
        """The bytes to write for `data`: encrypted while a login is set."""
        if not self.active:
            return data
        if self._key is None:
            raise PermissionError("The toolbox is locked: log in first")
        return MARK + self._key.encrypt(data)

    def _checked(self, password: str) -> Fernet | None:
        """The key that password makes, if it is the right one."""
        try:
            login = json.loads((self._folder / LOGIN_FILE).read_text(encoding="utf-8"))
            key = _key(password, base64.b64decode(login["salt"]), login["n"], login["r"], login["p"])
            return key if key.decrypt(login["check"].encode()) == CHECK else None
        except (OSError, ValueError, KeyError, TypeError, InvalidToken):
            return None

    def _files(self) -> list[Path]:
        if not self._folder.is_dir():
            return []
        return [file for file in sorted(self._folder.iterdir())
                if file.is_file() and file.name != LOGIN_FILE and not file.name.endswith(".tmp")]


def _key(password: str, salt: bytes, n: int = SCRYPT_N, r: int = SCRYPT_R, p: int = SCRYPT_P) -> Fernet:
    made = Scrypt(salt=salt, length=32, n=n, r=r, p=p).derive(password.encode("utf-8"))
    return Fernet(base64.urlsafe_b64encode(made))


def _replace(file: Path, data: bytes) -> None:
    """Writes the whole file or nothing: a cut-short write must not leave half a token."""
    half = file.with_name(file.name + ".tmp")
    half.write_bytes(data)
    half.replace(file)
