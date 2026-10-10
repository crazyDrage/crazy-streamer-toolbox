class FlowStepError(RuntimeError):
    """A box of a flow failed; the boxes after it (on its branch) didn't run."""

    def __init__(self, flow: str, node_id: str, action: str, cause: Exception) -> None:
        super().__init__(f"flow {flow!r} stopped at box {node_id} ({action}): {cause}")
        self.node_id = node_id
        self.action = action
        self.cause = cause
        self.results: list = []  # the boxes that did run, set by the FlowRunner
