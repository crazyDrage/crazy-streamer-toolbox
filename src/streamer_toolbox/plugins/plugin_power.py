import logging
from collections.abc import Callable

from streamer_toolbox.core.connections.connection_manager import ConnectionManager
from streamer_toolbox.core.interfaces.toolbox_plugin import ToolboxPlugin
from streamer_toolbox.plugins.plugin_switches import PluginSwitches

log = logging.getLogger(__name__)


class PluginPower:
    """What switching a plugin off and on does (his round 57: "off stops everything, even if it is used in a
    box"). Off: its stop() is called, its connection stops, its boxes refuse to run (why_not, also in flows
    that have them), its triggers start no flow, its listeners hear nothing, its tool, cards and page are gone.
    The flows keep its boxes; on again, everything works as before.

    `plugins()` gives the loaded plugins by id (PluginLoader.plugins); `connections` holds a plugin's own
    connection under the plugin's id, if it has one."""

    def __init__(self, switches: PluginSwitches, plugins: Callable[[], dict[str, ToolboxPlugin]],
                 connections: ConnectionManager | None = None) -> None:
        self._switches = switches
        self._plugins = plugins
        self.connections = connections  # set once the connections are made (they need is_off first)

    def is_off(self, plugin_id: str) -> bool:
        return plugin_id in self._plugins() and plugin_id in self._switches.off()

    def why_not(self, action_name: str) -> str:
        """For ActionRegistry.guard: why a box of a switched-off plugin can't run, "" for every other box."""
        plugin_id = action_name.split(".", 1)[0]
        if not self.is_off(plugin_id):
            return ""
        return f"The plugin {plugin_id} is switched off: switch it on under Plugins to use this box"

    async def start_all(self) -> None:
        """When the toolbox has started: start() of every plugin that is on."""
        for plugin_id, plugin in self._plugins().items():
            if not self.is_off(plugin_id):
                await self._call(plugin_id, plugin.start)

    async def stop_all(self) -> None:
        """When the toolbox closes: stop() of every plugin that is on (the others were stopped already)."""
        for plugin_id, plugin in self._plugins().items():
            if not self.is_off(plugin_id):
                await self._call(plugin_id, plugin.stop)

    async def switch(self, plugin_id: str, on: bool) -> None:
        if self.is_off(plugin_id) != on:
            return  # already so
        self._switches.switch(plugin_id, on)
        plugin = self._plugins().get(plugin_id)
        own = self.connections is not None and plugin_id in {c.id for c in self.connections.all()}
        if on:
            if plugin:
                await self._call(plugin_id, plugin.start)
            if own:
                await self.connections.resume(plugin_id)
        else:
            if own:
                await self.connections.pause(plugin_id)
            if plugin:
                await self._call(plugin_id, plugin.stop)

    @staticmethod
    async def _call(plugin_id: str, step: Callable) -> None:
        """One plugin's start or stop; one that fails is logged, the others still get theirs."""
        try:
            await step()
        except Exception as e:
            log.warning("plugin %s: %s failed: %s: %s", plugin_id, step.__name__, type(e).__name__, e)
