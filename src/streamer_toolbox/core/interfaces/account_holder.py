from abc import ABC, abstractmethod


class AccountHolder(ABC):
    """A streaming platform's connection that can have several accounts (his plan of 2026-11-05,
    docs/PLAN_multi_accounts.md; "the multi account option should be possible for every streaming platform",
    2026-11-06). Its tab shows the account list (gui/components/accounts_panel.py) from these; how an account is
    added is the platform's own (an AccountAdder).

    The main account is used wherever no account is picked. A bot account only writes (and moderates) in the
    main account's channel; another channel account can listen to its own channel."""

    title: str

    @abstractmethod
    def account_names(self) -> list[str]:
        """Every account it has, A to Z."""

    @abstractmethod
    def main_account(self) -> str:
        """The main account's name, "" when there is none."""

    @property
    @abstractmethod
    def multiple_accounts(self) -> bool:
        """His switch: boxes and triggers get an Account field."""

    @abstractmethod
    def is_bot(self, name: str) -> bool:
        """A bot account: writes in the main account's chat, never listens."""

    @abstractmethod
    def listens(self, name: str) -> bool:
        """Its own channel's events come in (always for the main account)."""

    @abstractmethod
    def account_state(self, name: str) -> str:
        """One line for the list: "connected", why not, or "" while the connection is off."""

    @abstractmethod
    def where_kept(self, name: str) -> str:
        """Where its login / key is kept, for the Remove question (e.g. config/secrets/twitch/name.json)."""

    @abstractmethod
    async def set_main_account(self, name: str) -> None:
        """His drop-down."""

    @abstractmethod
    def set_multiple_accounts(self, on: bool) -> None:
        """His switch."""

    @abstractmethod
    async def set_listening(self, name: str, on: bool) -> None:
        """Another account's own channel: its events come in too (off by default)."""

    @abstractmethod
    async def remove_account(self, name: str) -> None:
        """Forgets an account (its login / key)."""

    def has_bots(self) -> bool:
        """Whether the platform can have bot accounts (one that can write in chat)."""
        return False
