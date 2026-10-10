from collections.abc import Callable
from pathlib import Path

from nicegui import ui


class HelloBadge(ui.element, component=Path(__file__).parent.parent / "resources" / "hello_badge.js"):
    """The plugin's own JS component: shows the greeting count, and a click on it asks Python for a refresh."""

    icon_url = ""

    def __init__(self, count: Callable[[], int]) -> None:
        super().__init__()
        self._count = count
        self._props["icon"] = self.icon_url
        self._props["count"] = count()
        self.on("refresh", self._refresh)

    def _refresh(self) -> None:
        self._props["count"] = self._count()
        self.update()
