from abc import ABC, abstractmethod
from collections.abc import Callable


class AccountAdder(ABC):
    """How one platform adds an account on its tab (Twitch: a link and a code; YouTube: a login in a browser on
    this PC; Rumble: another Live Stream API address; Fansly: another chatroom). The account list itself is
    AccountsPanel's, the same for every platform."""

    @abstractmethod
    def build(self, added: Callable[[], None]) -> None:
        """The inside of "Add account"; `added()` once an account is in the list."""

    def logs_in_again(self) -> bool:
        """Whether a row gets a "Log in again" button (a login that can expire)."""
        return False

    def log_in_again(self, name: str) -> None:
        """That button: the same login as Add account, for this account."""
