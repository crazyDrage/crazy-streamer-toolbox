"""The example plugin's entry point. Start reading here; README.md next to this file is the tour.

The toolbox finds this folder at start, reads plugin.json, creates the one class below and calls its
`register(ctx)` once. Everything the plugin adds to the toolbox goes through `ctx`. There is no other door,
and nothing else in this folder is called by the toolbox by itself."""
from pathlib import Path

from fastapi import APIRouter
from nicegui import ui

from streamer_toolbox.core.interfaces.plugin_context import PluginContext
from streamer_toolbox.core.interfaces.toolbox_plugin import ToolboxPlugin

from .lib.event_counter import EventCounter
from .lib.lamp_connection import LampConnection
from .lib.lamp_tool import LampTool
from .lib.pretend_lamp import COLORS, PretendLamp

README = Path(__file__).parent / "README.md"


class ExamplePlugin(ToolboxPlugin):
    """One plugin with everything a plugin can add. The numbers match README.md."""

    def register(self, ctx: PluginContext) -> None:
        lamp = PretendLamp()      # the "program" (lib/pretend_lamp.py)
        seen = EventCounter()     # counts what happens in the toolbox (lib/event_counter.py)

        # 1 · A TRIGGER: something that can start a flow.
        #     Tell the toolbox the event exists: its name, its title in the Start box, and its fields (the
        #     dots a flow can wire from). Its full name is "<plugin id>.<event>" = "example.blinked".
        #     pick= is the one field a flow's trigger is matched on ("only when the colour is red"), and
        #     example= what that input starts with (* = any). choices= makes that input a DROPDOWN: a list,
        #     or an async function that returns one (like a box's options=). Typing still works, so a
        #     pattern like "r*" stays possible. description= is the line under its name in Add trigger.
        ctx.add_trigger("blinked", "Example lamp blinked", fields=("times", "color"), icon="lightbulb",
                        pick="color", example="*", choices=("*", *COLORS),
                        description="The example lamp finished blinking")

        # 2 · A CONNECTION: a program with its own tab under Connections (lib/lamp_connection.py).
        #     It brings its boxes along (lib/lamp_actions.py). The second argument is how the lamp's boxes
        #     report "I blinked": ctx.publish sends the event from step 1, and flows with that trigger start.
        ctx.add_connection(LampConnection(lamp, blinked=lambda data: ctx.publish("blinked", data)))

        # 3 · A BOX without a connection: the short way, for a plugin that has no program to talk to.
        #     The name becomes "example.shout". The function's parameters are the box's fields.
        async def shout(text: str = "hello", times: int = 1) -> dict[str, str]:
            return {"text": " ".join([str(text).upper() + "!"] * max(int(times), 1))}

        ctx.add_action("shout", shout, "Makes a text loud", label="Shout", outputs={"text": "text"},
                       hints={"text": "What to shout", "times": "How often"})

        # 4 · ASKING THE STREAMER: a yes / no popup on every open toolbox screen. None = nobody answered.
        #     This box also shows how a plugin runs another action: ctx.run_action("<name>", fields...).
        async def ask_then_blink() -> dict[str, bool]:
            answer = await ctx.ask_yes_no("Blink the example lamp?", timeout=20)
            if answer:
                await ctx.run_action("example.blink", times=2)
            return {"blinked": bool(answer)}

        ctx.add_action("ask_then_blink", ask_then_blink, "Asks on screen first, then blinks",
                       label="Ask, then blink", outputs={"blinked": "yes/no"})

        # 5 · LISTENING: hear every event of the toolbox.
        ctx.on_event(seen.heard)

        # 6 · SCREENS, all drawn with NiceGUI (lib/lamp_tool.py):
        tool = LampTool(ctx, lamp, seen)
        ctx.add_tool("Example lamp", tool.build, icon="lightbulb",        # a page under Tools
                     description="The example plugin's tool")
        ctx.add_panel("Example lamp", tool.card, section="live")          # a card on Live
        #                                         (or "connections" / "settings")
        ctx.add_page("Example plugin", self._page, icon="menu_book")      # a page of its own, in the menu

        # 7 · AN API ROUTE of its own, for other programs: GET /api/plugins/example/lamp
        #     (Every action is in the API already as POST /action/example.<name>; a route is for more.)
        router = APIRouter()

        @router.get("/lamp")
        def lamp_state() -> dict:
            return {"on": lamp.on, "color": lamp.color, "blinks": lamp.blinks}

        ctx.add_router(router)

        # Not shown as code here, used in lib/lamp_tool.py:
        # 8 · SETTINGS: ctx.settings() / ctx.save_settings({...}); defaults in resources/settings.json
        # 9 · FILES: ctx.resource_url("lamp.svg") is the address of a file in resources/

    @staticmethod
    def _page() -> None:
        """The plugin's own page shows the tour, so it can be read inside the toolbox too."""
        ui.markdown(README.read_text(encoding="utf-8"))
