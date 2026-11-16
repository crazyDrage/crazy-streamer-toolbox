from contextvars import ContextVar

# (the flow's name, the box's id) of the box that runs right now in a flow; None on Live, the API, SAMMI. A box
# that keeps things per box (Keep media locally: its own folder and address) reads it
current_box: ContextVar[tuple[str, str] | None] = ContextVar("current_box", default=None)
# the run dot (one of the box's `starts`) a wire started the box at; "" = its normal one, and outside a flow
started_at: ContextVar[str] = ContextVar("started_at", default="")
