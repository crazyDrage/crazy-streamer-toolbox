from contextvars import ContextVar

# (the flow's name, the box's id) of the box that runs right now in a flow; None on Live, the API, SAMMI. A box
# that keeps things per box (Keep media locally: its own folder and address) reads it
current_box: ContextVar[tuple[str, str] | None] = ContextVar("current_box", default=None)
