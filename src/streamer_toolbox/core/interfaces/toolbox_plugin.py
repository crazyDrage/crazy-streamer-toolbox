from abc import ABC, abstractmethod

from streamer_toolbox.core.interfaces.plugin_context import PluginContext


class ToolboxPlugin(ABC):
    """What every plugin implements. The toolbox calls register() once at startup."""

    @abstractmethod
    def register(self, ctx: PluginContext) -> None:
        """Add the plugin's actions, API routes, pages and panels through ctx."""
