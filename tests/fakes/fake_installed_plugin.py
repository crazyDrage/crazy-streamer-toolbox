from streamer_toolbox.core.interfaces.toolbox_plugin import ToolboxPlugin


class FakeInstalledPlugin(ToolboxPlugin):
    """A plugin as a pip package would provide it through an entry point."""

    def register(self, ctx) -> None:
        async def ping() -> str:
            return "pong"
        ctx.add_action("ping", ping)
