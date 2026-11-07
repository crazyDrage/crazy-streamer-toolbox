"""Which account of a connection the running work is for (his plan of 2026-11-05: docs/PLAN_multi_accounts.md).
A box's Account field sets it for its one run, an account's own event listener for what it hears; "" (nothing
set) means the main account (his answer 122: an empty field always means the main account, also after the main
account changed). Async tasks started from there carry it along by themselves."""
from contextvars import ContextVar

ACCOUNT: ContextVar[str] = ContextVar("account", default="")
