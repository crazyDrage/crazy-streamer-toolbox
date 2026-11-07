import logging
import re
from collections.abc import Callable
from pathlib import Path

from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.connections.oauth.oauth_token_store import OAuthTokenStore
from streamer_toolbox.connections.oauth.token_keeper import TokenKeeper

log = logging.getLogger(__name__)
NAME = re.compile(r"[a-z0-9_]+")  # a Twitch login: letters, digits and _ (also safe as a file name)
ENDING = ".json"


class AccountTokens(TokenKeeper):
    """A connection's logins, one file per account in its own folder, named after the account (his plan of
    2026-11-05, answer 118: the Twitch login), e.g. config/secrets/twitch/crazydrage.json. One of them is the
    main account (the connection's setting main_account, his drop-down): load / save / clear are about it, so
    everything that knew one login keeps working with the main account.

    `path_of(file name)` gives the file's path (a SecretPath: encrypted with a toolbox login), `folder` is
    where they lie, `main()` reads the main account's name and `set_main(name)` saves it."""

    def __init__(self, folder: Path, path_of: Callable[[str], Path], main: Callable[[], str],
                 set_main: Callable[[str], None], fit: Callable[[str], str] | None = None) -> None:
        self._folder = folder
        self._fit = fit or _name  # a login → the account's name ("" = doesn't fit; YouTube: made to fit)
        self._path_of = path_of
        self._main = main
        self._set_main = set_main

    # ---- the main account (TokenKeeper) ----

    def load(self) -> OAuthToken | None:
        name = self.main_name()
        return self.load_account(name) if name else None

    def save(self, token: OAuthToken) -> None:
        """Keeps a login of the main account: Connect logs in as the main account, so the account it comes
        back with is the main one from now on (another one he had stays in the list)."""
        name = self.save_account(token)
        if name != self._main():
            self._set_main(name)

    def clear(self) -> None:
        name = self.main_name()
        if name:
            self.remove(name)

    # ---- every account ----

    def names(self) -> list[str]:
        """Every account that has a login, A to Z."""
        if not self._folder.is_dir():
            return []
        return sorted(p.name[:-len(ENDING)] for p in self._folder.iterdir()
                      if p.name.endswith(ENDING) and NAME.fullmatch(p.name[:-len(ENDING)]))

    def main_name(self) -> str:
        """The main account: the one his setting names, else (that one is gone) the first there is, "" when
        there is none."""
        names = self.names()
        chosen = str(self._main() or "").strip().casefold()
        if chosen in names:
            return chosen
        return names[0] if names else ""

    def set_main(self, name: str) -> None:
        """His drop-down: another account is the main one (it must have a login)."""
        if name not in self.names():
            raise KeyError(f"there is no account {name!r}")
        self._set_main(name)

    def load_account(self, name: str) -> OAuthToken | None:
        return self._store(name).load() if NAME.fullmatch(name or "") else None

    def save_account(self, token: OAuthToken, was: str = "") -> str:
        """Keeps one account's login under its name; its name. An account Twitch renamed (same user id, other
        login) moves to its new name, and stays the main account if it was. `was`: the name the login was read
        under (a check that came back with another name moves it too: an old file without its name)."""
        name = self._fit(token.login) or self.main_name() or "account"
        renamed = [old for old in self.names() if old != name and (old == was or
                                                                    self._user_id(old) == token.user_id != "")]
        self._store(name).save(token)
        for old in renamed:
            self.remove(old)
            log.info("account %s is called %s now", old, name)
            if old == str(self._main() or "").casefold():
                self._set_main(name)
        return name

    def remove(self, name: str) -> None:
        """Forgets one account's login (its file)."""
        if NAME.fullmatch(name or ""):
            self._store(name).clear()

    def move_single_file(self, old: TokenKeeper) -> str:
        """Once, after the update to accounts: the one login kept so far (twitch_token.json) becomes an account
        in the folder and the main account, so nobody has to log in again. The account's name, or "" when there
        was nothing to move."""
        token = old.load()
        if token is None:
            return ""
        name = self.save_account(token)
        if not self._main():
            self._set_main(name)
        old.clear()
        log.info("the login of %s moved into the accounts folder", name)
        return name

    def _store(self, name: str) -> OAuthTokenStore:
        return OAuthTokenStore(self._path_of(name + ENDING))

    def _user_id(self, name: str) -> str:
        token = self.load_account(name)
        return token.user_id if token else ""


def _name(login: str) -> str:
    name = str(login or "").strip().casefold()
    return name if NAME.fullmatch(name) else ""
