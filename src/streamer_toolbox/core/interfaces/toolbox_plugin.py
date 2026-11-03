from abc import ABC, abstractmethod

from streamer_toolbox.core.interfaces.plugin_context import PluginContext


class ToolboxPlugin(ABC):
    """What every plugin implements. The toolbox calls register() once at startup. start() and stop() are
    optional: start() when the toolbox has started and when he switches the plugin on again (Plugins), stop()
    when he switches it off and when the toolbox closes."""

    @abstractmethod
    def register(self, ctx: PluginContext) -> None:
        """Add what the plugin has through ctx.add(...): its boxes, triggers, connection, tools, pages, ..."""

    async def start(self) -> None:
        """Start what the plugin runs itself, like a timer or a socket. Not for adding things: that is
        register()."""

    async def stop(self) -> None:
        """Let go of what start() started. Its connection is stopped by the toolbox, like every connection."""
