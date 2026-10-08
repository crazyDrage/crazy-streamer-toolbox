import logging
import re

from nicegui import ui

from streamer_toolbox.gui.services.ui_registry import UiRegistry

log = logging.getLogger(__name__)


class ToolsPage:
    """Tools: the tools plugins added (ctx.add_tool), e.g. SAMMI decks as buttons. /tools is the overview: one
    card per tool. /tools?show=<tool_slug of its title> is that tool alone (the side menu lists them under
    Tools). A tool that fails to draw shows its error instead of taking the page down."""

    def __init__(self, ui_registry: UiRegistry) -> None:
        self._ui = ui_registry

    def build(self) -> None:
        tools = self._ui.tools
        if not tools:
            ui.label("No tools yet. Plugins add them (ctx.add_tool); see docs/PLUGINS.md.").classes("opacity-70")
            return
        shown = ui.context.client.request.query_params.get("show", "")
        tool = next((tool for tool in tools if shown and tool_slug(tool[1]) == shown), None)
        if tool is None:
            self._overview()
            return
        plugin_id, title, icon, _description, builder = tool
        ui.link("← All tools", "/tools").classes("text-sm")
        with ui.row().classes("items-center gap-2"):
            ui.icon(icon or "handyman").classes("text-2xl text-primary")
            ui.label(title).classes("text-lg font-semibold")
        try:
            builder()
        except Exception as e:  # a broken tool shows why, not an error page
            log.exception("tool %s of plugin %s failed", title, plugin_id)
            ui.label(f"This tool failed to open: {type(e).__name__}: {e}").classes("text-negative")

    def _overview(self) -> None:
        with ui.element("div").classes("grid gap-3 w-full sm:grid-cols-2 xl:grid-cols-3 items-stretch"):
            for _, title, icon, description, _builder in self._ui.tools:
                with ui.link(target=f"/tools?show={tool_slug(title)}").classes("no-underline text-inherit"), \
                        ui.card().classes("w-full h-full gap-1 cursor-pointer hover:bg-gray-500/10"):
                    with ui.row().classes("items-center no-wrap gap-2 w-full"):
                        ui.icon(icon or "handyman").classes("text-2xl text-primary")
                        ui.label(title).classes("text-lg font-semibold flex-1")
                    ui.label(description).classes("text-xs opacity-70")


def tool_slug(title: str) -> str:
    """A tool's title as it is in an address: "SAMMI decks" → "sammi_decks"."""
    return re.sub(r"[^a-z0-9]+", "_", title.casefold()).strip("_")
