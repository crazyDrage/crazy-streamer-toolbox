from dataclasses import dataclass, field
from typing import Any

from streamer_toolbox.core.deck.deck_button import COLORS, DeckButton
from streamer_toolbox.core.deck.deck_page import DeckPage
from streamer_toolbox.core.flows.flow import Flow


@dataclass
class Deck:
    """The Live page's buttons on pages (tabs), like a Deck Hopper / SAMMI deck."""

    pages: list[DeckPage] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Deck":
        return cls([DeckPage.from_dict(p) for p in data.get("pages", [])])

    def to_dict(self) -> dict[str, Any]:
        return {"pages": [p.to_dict() for p in self.pages]}

    @classmethod
    def from_flows(cls, flows: list[Flow]) -> "Deck":
        """The starting deck: one page with a button per flow, colours taking turns."""
        buttons = [DeckButton(f.label, f.action_name, color=COLORS[i % len(COLORS)])
                   for i, f in enumerate(sorted(flows, key=lambda f: f.label.casefold()))]
        page = DeckPage("Flows", buttons)
        page.place()
        return cls([page])

    def page(self, name: str) -> DeckPage | None:
        return next((p for p in self.pages if p.name == name), None)

    def free_page_name(self, wanted: str = "Page") -> str:
        names = {p.name for p in self.pages}
        if wanted not in names:
            return wanted
        number = 2
        while f"{wanted} {number}" in names:
            number += 1
        return f"{wanted} {number}"
