from collections.abc import Callable

from streamer_toolbox.core.interfaces.connection import Connection

SECTIONS = ("live", "connections", "settings")  # where a plugin panel can go


class UiRegistry:
    """What plugins add to the GUI: their own pages (in the Plugins tab's side list, under the plugin), panels
    (Connections, or under Plugins → the plugin), tabs on the Tools page, a display name per action category, and their connections."""

    def __init__(self) -> None:
        self.pages: list[tuple[str, str, str]] = []                        # (title, path, icon)
        self.panels: list[tuple[str, str, str, Callable[[], None]]] = []   # (plugin_id, section, title, builder)
        # the Tools page: (plugin_id, title, icon, description, builder), one tab each
        self.tools: list[tuple[str, str, str, str, Callable[[], None]]] = []
        self.category_titles: dict[str, str] = {"obs": "OBS"}
        self.connections: list[Connection] = []  # a plugin's own program, shown under Connections

    def panels_for(self, section: str) -> list[tuple[str, str, Callable[[], None]]]:
        return [(pid, title, builder) for pid, sec, title, builder in self.panels if sec == section]
