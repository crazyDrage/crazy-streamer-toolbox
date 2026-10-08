from dataclasses import dataclass, field


@dataclass(frozen=True)
class OutlineEntry:
    """One line of a flow shown as a list.

    kind "node": the box node_id; its branches are its outputs when it has several (If: "then", "else").
    kind "parallel": boxes that start at the same time; each branch (label "") is one of them and what follows it.
    kind "ref": the box node_id was already shown higher up (two wires lead into it).
    """

    kind: str
    node_id: str = ""
    branches: tuple[tuple[str, tuple["OutlineEntry", ...]], ...] = field(default_factory=tuple)
