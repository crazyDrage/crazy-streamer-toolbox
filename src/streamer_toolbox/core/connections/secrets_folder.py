import logging
from pathlib import Path

from streamer_toolbox.core.connections.secret_path import SecretPath
from streamer_toolbox.core.security.secret_vault import SecretVault

log = logging.getLogger(__name__)
NAME = "secrets"


class SecretsFolder:
    """Where the tokens, keys, passwords and logins live: the sub folder `secrets` of the settings folder
    (config/secrets/), apart from the settings, flows and caches that are fine to look at or to copy.

    path() gives a SecretPath: with a login set (Settings → Login, `vault`) the file is encrypted on disk.

    The files used to lie in the settings folder itself. path() moves such a file over the first time it is
    asked for, so nobody has to type a token again; when the move fails (the file is open somewhere), the old
    place keeps being used and the next start tries again. On Linux and macOS the folder is the owner's only
    (700); on Windows the settings folder already belongs to the user's account."""

    def __init__(self, settings_folder: Path) -> None:
        self._old = settings_folder
        self.folder = settings_folder / NAME
        self.vault = SecretVault(self.folder)

    def path(self, name: str) -> Path:
        """The file of that name in the secrets folder (it need not exist yet)."""
        new, old = SecretPath(self.folder / name, vault=self.vault), self._old / name
        if new.exists() or not old.is_file():
            return new
        try:
            self._make()
            if self.vault.active:  # a login is set: the file must not lie there plain
                new.write_bytes(old.read_bytes())
                old.unlink()
            else:
                old.replace(new)
        except OSError as e:
            log.warning("%s stays in the settings folder for now (%s)", name, e)
            return old
        return new

    def _make(self) -> None:
        if not self.folder.is_dir():
            self.folder.mkdir(parents=True)
            self.folder.chmod(0o700)  # Windows only knows read-only here: nothing changes there
