import logging
import re
from collections.abc import Callable
from pathlib import Path

log = logging.getLogger(__name__)
NAME = re.compile(r"[a-z0-9_]+")  # an account's name: letters, digits and _ (also safe as a file name)
ENDING = ".txt"


class AccountKeys:
    """A connection's keys (an address, a token) when it has several accounts and no login: one text file per
    account in its own folder, named after the account, e.g. config/secrets/rumble/crazydrage.txt (his plan
    docs/PLAN_multi_accounts.md, for every streaming platform since 2026-11-06). One of them is the main account
    (the connection's setting main_account).

    `path_of(file name)` gives the file's path (a SecretPath: encrypted with a toolbox login), `folder` is where
    they lie, `main()` reads the main account's name and `set_main(name)` saves it."""

    def __init__(self, folder: Path, path_of: Callable[[str], Path], main: Callable[[], str],
                 set_main: Callable[[str], None]) -> None:
        self._folder = folder
        self._path_of = path_of
        self._main = main
        self._set_main = set_main

    def names(self) -> list[str]:
        if not self._folder.is_dir():
            return []
        return sorted(p.name[:-len(ENDING)] for p in self._folder.iterdir()
                      if p.name.endswith(ENDING) and NAME.fullmatch(p.name[:-len(ENDING)]))

    def main_name(self) -> str:
        names = self.names()
        chosen = str(self._main() or "").strip().casefold()
        if chosen in names:
            return chosen
        return names[0] if names else ""

    def set_main(self, name: str) -> None:
        if name not in self.names():
            raise KeyError(f"there is no account {name!r}")
        self._set_main(name)

    def load(self, name: str) -> str:
        """The account's key, "" when there is none."""
        if not NAME.fullmatch(name or ""):
            return ""
        path = self._path_of(name + ENDING)
        return path.read_text(encoding="utf-8").strip() if path.exists() else ""

    def save(self, name: str, key: str) -> str:
        """Keeps an account's key under its name (made fit: letters, digits, _); the name. The first account is
        the main one."""
        name = fit_name(name) or "account"
        path = self._path_of(name + ENDING)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(key.strip() + "\n", encoding="utf-8")
        if not str(self._main() or "").strip():
            self._set_main(name)
        return name

    def rename(self, old: str, new: str) -> str:
        """An account that turned out to have another name (the moved one): its key moves; the main account
        stays the main account."""
        new = fit_name(new)
        if not new or new == old or not self.load(old):
            return old
        was_main = old == self.main_name()
        self.save(new, self.load(old))
        self.remove(old)
        if was_main:
            self._set_main(new)
        return new

    def remove(self, name: str) -> None:
        if NAME.fullmatch(name or ""):
            path = self._path_of(name + ENDING)
            if path.exists():
                path.unlink()

    def move_single_file(self, old: Path, name: str) -> str:
        """Once, after the update to accounts: the one key kept so far becomes an account (the main one) in the
        folder. The account's name, "" when there was nothing to move."""
        key = old.read_text(encoding="utf-8").strip() if old.exists() else ""
        if not key:
            return ""
        name = self.save(name, key)
        if not self._main():
            self._set_main(name)
        old.unlink()
        log.info("the key of %s moved into the accounts folder", name)
        return name


def fit_name(text: str) -> str:
    """A name as the toolbox keeps it: lower case letters, digits and _."""
    return re.sub(r"[^a-z0-9_]+", "_", str(text or "").casefold()).strip("_")
