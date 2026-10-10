from dataclasses import dataclass


@dataclass(frozen=True)
class FlowInput:
    """A value the flow asks for when it runs, used in steps as ${input.<name>}. Without a default it's required
    (the Live page asks for it; SAMMI or a redeem passes it)."""

    name: str
    default: str | None = None
    description: str = ""
