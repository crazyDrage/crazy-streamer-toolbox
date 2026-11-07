import inspect
from typing import Any

from streamer_toolbox.core.actions.registered_action import ActionHandler
from streamer_toolbox.core.connections.current_account import ACCOUNT

ACCOUNT_FIELD = "account"


class AccountHandler:
    """A box of a connection with several accounts, with one more field: Account (his plan of 2026-11-05,
    docs/PLAN_multi_accounts.md, step 3). The box's own run never sees it: for that one run the account is the
    connection's current account (current_account.ACCOUNT), "" = the main one (his answer 122)."""

    def __init__(self, handler: ActionHandler) -> None:
        self._handler = handler
        own = inspect.signature(handler)
        parameters = list(own.parameters.values())
        extra = inspect.Parameter(ACCOUNT_FIELD, inspect.Parameter.KEYWORD_ONLY, default="", annotation=str)
        spread = [p for p in parameters if p.kind == p.VAR_KEYWORD]  # a **values stays last
        self.__signature__ = own.replace(parameters=[p for p in parameters if p.kind != p.VAR_KEYWORD]
                                         + [extra] + spread)

    @property
    def handler(self) -> ActionHandler:
        """The box's own run."""
        return self._handler

    async def __call__(self, *args: Any, account: Any = "", **params: Any) -> Any:
        mark = ACCOUNT.set(str(account or "").strip().lstrip("@").casefold())
        try:
            return await self._handler(*args, **params)
        finally:
            ACCOUNT.reset(mark)
