"""The plugin's entry point: everything it adds to the toolbox is collected in register()."""
from fastapi import APIRouter
from nicegui import ui

from streamer_toolbox.core.interfaces.plugin_context import PluginContext
from streamer_toolbox.core.interfaces.toolbox_plugin import ToolboxPlugin

from .lib.hello_badge import HelloBadge


class HelloPlugin(ToolboxPlugin):
    """Example plugin showing every extension point: actions, an API route, a page, a panel, a tool, its own JS
    and a picture from resources/, and settings."""

    def __init__(self) -> None:
        self.greetings = 0

    def register(self, ctx: PluginContext) -> None:
        HelloBadge.icon_url = ctx.resource_url("wave.svg")

        async def greet(name: str = "chat") -> str:
            self.greetings += 1
            return f"hello {name} (#{self.greetings})"

        async def ask() -> str:
            answer = await ctx.ask_yes_no("Say hello to chat?", timeout=20)
            if answer is None:
                return "nobody answered"
            return await greet() if answer else "ok, not now"

        ctx.add_action("greet", greet, "Counts greetings", label="Say hello")
        ctx.add_action("ask", ask, "Asks yes/no on every open screen first", label="Ask, then say hello")

        router = APIRouter()

        @router.get("/count")
        def count() -> dict:
            return {"greetings": self.greetings}

        ctx.add_router(router)
        ctx.add_page("Hello", self._page, icon="waving_hand")
        ctx.add_panel("Hello", lambda: HelloBadge(lambda: self.greetings))
        ctx.add_tool("Hello", lambda: self._tool(ctx), icon="waving_hand", description="The example plugin's tool")

    @staticmethod
    def _tool(ctx: PluginContext) -> None:
        """A tool tab with a setting that's kept (ctx.settings / ctx.save_settings)."""
        name = ui.input("say hello to", value=ctx.settings().get("name", "chat")).props("outlined dense")

        async def hello() -> None:
            ctx.save_settings({"name": name.value})
            ui.notify(await ctx.run_action("hello.greet", name=name.value))

        ui.button("Say hello", icon="waving_hand", on_click=hello).props("no-caps unelevated")

    def _page(self) -> None:
        ui.markdown("This page comes from `plugins/hello/`. The badge below is the plugin's own Vue component "
                    "(`resources/hello_badge.js`).")
        HelloBadge(lambda: self.greetings)
