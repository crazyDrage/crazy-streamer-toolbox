from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LearnTopic:
    """One page of the Learn tab: a text, and maybe an example flow next to it (`flows`, a .flows.toml file
    that "Add to my flows" copies, switched off)."""

    id: str
    title: str
    section: str
    text: str
    order: int = 0
    flows: Path | None = None
