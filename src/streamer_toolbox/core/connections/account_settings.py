from collections.abc import Callable, Iterable
from typing import Any

# a connection's settings for its accounts (toolbox.toml, its table)
ACCOUNT_DEFAULTS: dict[str, Any] = {"main_account": "", "multiple_accounts": False, "bot_accounts": [],
                                    "listen": []}


class AccountSettings:
    """The account settings every connection with several accounts has (his plan of 2026-11-05, for every
    streaming platform since 2026-11-06): main_account, multiple_accounts (boxes and triggers get an Account
    field), bot_accounts, listen (other accounts whose own channel's events come in too).

    `settings()` reads the connection's settings as they are now; `save(values)` keeps changed ones."""

    def __init__(self, settings: Callable[[], dict[str, Any]], save: Callable[[dict[str, Any]], None]) -> None:
        self._settings = settings
        self._save = save

    @property
    def multiple(self) -> bool:
        return bool(self._settings().get("multiple_accounts"))

    def set_multiple(self, on: bool) -> None:
        self._save({"multiple_accounts": bool(on)})

    def is_bot(self, name: str) -> bool:
        return name in self._list("bot_accounts")

    def set_bot(self, name: str, bot: bool) -> None:
        bots = [n for n in self._list("bot_accounts") if n != name] + ([name] if bot else [])
        self._save({"bot_accounts": sorted(bots)})

    def listens(self, name: str, main: str) -> bool:
        return name == main or name in self._list("listen")

    def set_listening(self, name: str, on: bool) -> None:
        others = [n for n in self._list("listen") if n != name] + ([name] if on else [])
        self._save({"listen": sorted(others)})

    def forget(self, name: str) -> None:
        """A removed account: out of the bot and listen lists."""
        self._save({"bot_accounts": [n for n in self._list("bot_accounts") if n != name],
                    "listen": [n for n in self._list("listen") if n != name]})

    def listening(self, main: str, usable: Iterable[str]) -> list[str]:
        """The accounts whose own channel's events come in: the main one first, then the others he switched on
        that are usable now (a bot account has no channel of interest)."""
        usable = set(usable)
        return [name for name in dict.fromkeys([main, *sorted(self._list("listen"))])
                if name and name in usable and (name == main or not self.is_bot(name))]

    def _list(self, key: str) -> list[str]:
        value = self._settings().get(key) or []
        return [str(v) for v in value] if isinstance(value, list) else []
