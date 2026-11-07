import abc

from streamer_toolbox.connections.oauth.oauth_token import OAuthToken


class TokenKeeper(abc.ABC):
    """Where a connection keeps its login: one file (OAuthTokenStore) or one per account with a main one
    (AccountTokens, his plan of 2026-11-05: docs/PLAN_multi_accounts.md)."""

    @abc.abstractmethod
    def load(self) -> OAuthToken | None:
        """The login (the main account's), None without one."""

    @abc.abstractmethod
    def save(self, token: OAuthToken) -> None:
        """Keeps the login (as the main account's)."""

    @abc.abstractmethod
    def clear(self) -> None:
        """Forgets the login (the main account's)."""
