class FlowSkipped(RuntimeError):
    """A flow set to "skip when busy" was started while it still ran; this start did nothing."""
