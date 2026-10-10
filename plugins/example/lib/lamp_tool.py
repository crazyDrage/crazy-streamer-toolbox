from nicegui import ui

from streamer_toolbox.core.interfaces.plugin_context import PluginContext

from .event_counter import EventCounter
from .pretend_lamp import COLORS, PretendLamp


class LampTool:
    """The lamp's TOOL: a page under Tools, drawn with NiceGUI (nicegui.io: `ui.button`, `ui.label`,
    `ui.select`, ...). The small card on the Live page (`card`) is drawn the same way.

    Three rules that save trouble:
      - `build()` runs once for every browser tab that opens the tool. Create the inputs inside it, not in
        `__init__`: this one object is shared by all open pages.
      - A button does not touch the lamp itself. It runs the plugin's own ACTION (`ctx.run_action`), so the
        tool, a flow, the SAMMI deck and the API all go the same way and say the same things when the lamp
        is off.
      - What should outlive a restart goes into the settings (`ctx.settings()` / `ctx.save_settings()`)."""

    def __init__(self, ctx: PluginContext, lamp: PretendLamp, seen: EventCounter) -> None:
        self._ctx = ctx
        self._lamp = lamp
        self._seen = seen

    def build(self) -> None:
        settings = self._ctx.settings()  # resources/settings.json, with what was saved on top

        @ui.refreshable
        def state() -> None:
            with ui.row().classes("items-center gap-3"):
                ui.image(self._ctx.resource_url("lamp.svg")).classes("w-10")  # a file from resources/
                ui.icon("circle").classes("text-4xl") \
                    .style(f"color: {COLORS[self._lamp.color] if self._lamp.on else '#555'}")
                ui.label(f"{'on' if self._lamp.on else 'off'} · {self._lamp.color} · blinked "
                         f"{self._lamp.blinks} times")
            ui.label(f"Events the plugin heard since the start: {self._seen.count}"
                     + (f" (last: {self._seen.last})" if self._seen.last else "")).classes("text-xs opacity-60")

        state()
        ui.timer(1.0, state.refresh)  # the lamp can change from a flow at any time: look again every second

        color = ui.select(list(COLORS), value=self._lamp.color, label="Colour").props("outlined dense") \
            .classes("w-40")
        times = ui.number("Blink how often", value=settings.get("blink_times", 3), min=1, max=20, step=1) \
            .props("outlined dense").classes("w-40")

        async def set_color() -> None:
            await self._run("example.set_color", color=color.value)

        async def blink() -> None:
            how_often = int(times.value or 3)  # an emptied number input gives None
            self._ctx.save_settings({"blink_times": how_often})  # remembered after a restart
            await self._run("example.blink", times=how_often)

        with ui.row().classes("gap-2"):
            ui.button("Set colour", icon="palette", on_click=set_color).props("no-caps unelevated")
            ui.button("Blink", icon="flare", on_click=blink).props("no-caps unelevated")

    def card(self) -> None:
        """The card on the Live page: one button."""
        async def blink() -> None:
            await self._run("example.blink", times=int(self._ctx.settings().get("blink_times", 3)))

        ui.button("Blink the example lamp", icon="flare", on_click=blink).props("no-caps flat")

    async def _run(self, action: str, **values) -> None:
        try:
            await self._ctx.run_action(action, **values)
        except Exception as e:  # the action's own words: "The example lamp is switched off under …"
            ui.notify(str(e), type="warning")
