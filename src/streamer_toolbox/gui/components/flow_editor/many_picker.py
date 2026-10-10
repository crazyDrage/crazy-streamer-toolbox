from collections.abc import Awaitable, Callable

from nicegui import app, ui

ON, OFF = "check_box", "check_box_outline_blank"
CHOSEN = "bg-primary/20"
LIGHT_KEY, LIGHT_COLOR_KEY = "many_light", "many_light_color"  # app.storage.general: the switch and its colour
LIGHT_COLOR = "#FF00FF"
Light = Callable[[str, str], Awaitable[None]]  # (choice, colour) lights that one up; ("", ...) takes it away


class ManyPicker:
    """A window to pick several from a list (the parts of a VTube Studio model): a search on top, one row per
    choice. A click ticks a row or takes its tick away; holding the mouse button and moving over more rows
    paints them the same way, so a run of parts is one stroke. "All shown" / "None shown" work on what the
    search leaves. A value that is set but not in the list (typed, or from another model) stays as a row.

    With `light` (RegisteredAction.lights) the window has a switch and a colour: while it is on, the row under
    the mouse is lit up in the program (the part on the model), so a name like ArtMesh37 can be found by
    looking. Only the newest row is sent while the program is still busy with the one before; it is taken
    away when the mouse leaves the list, the switch goes off or the window closes."""

    def __init__(self, choices: list[str], chosen: list[str], light: Light | None = None) -> None:
        self._choices = list(dict.fromkeys([*choices, *chosen]))
        self._chosen = set(chosen)
        self._rows: dict[str, tuple[ui.element, ui.icon]] = {}
        self._paint = True  # what a stroke does to the rows it crosses: tick them, or take the tick away
        self._light = light
        self._lighting = bool(light) and bool(app.storage.general.get(LIGHT_KEY, False))
        self._color = str(app.storage.general.get(LIGHT_COLOR_KEY, LIGHT_COLOR)) if light else LIGHT_COLOR
        self._wanted = self._lit = ""  # the row the mouse is on, and the one the program shows lit
        self._busy = False

    async def pick(self, title: str) -> list[str] | None:
        """Opens the window; the chosen ones in the list's order, or None when it was closed without Use."""
        with ui.dialog() as dialog, ui.card().classes("w-[32rem] max-w-full h-[80vh] gap-2 p-3"):
            with ui.row().classes("items-center w-full no-wrap gap-2"):
                ui.label(title).classes("text-lg font-semibold")
                search = ui.input(placeholder="Search").props("autofocus clearable dense outlined debounce=150") \
                    .classes("flex-1")
            with ui.row().classes("items-center w-full gap-2"):
                self._count = ui.label().classes("text-sm opacity-70 flex-1")
                ui.button("All shown", on_click=lambda: self._all(True)).props("flat dense no-caps")
                ui.button("None shown", on_click=lambda: self._all(False)).props("flat dense no-caps")
            if self._light:
                self._light_row()
            ui.label("Click to tick. Hold the mouse button and move over the rows to tick many.") \
                .classes("text-xs opacity-60")
            with ui.element("div").classes("flex-1 min-h-0 w-full overflow-y-auto select-none") as rows:
                for choice in self._choices:
                    self._row(choice)
            rows.on("mouseleave", lambda: self._point(""))
            if not self._choices:
                ui.label("The list is empty.").classes("opacity-70")
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat no-caps")
                ui.button("Use", on_click=lambda: dialog.submit(self.chosen())).props("unelevated no-caps")
            search.on_value_change(lambda e: self._show(e.value or ""))
            self._counted()
        try:
            result = await dialog
        finally:
            self._lighting = False
            await self._point("", force=True)
        dialog.delete()
        return result

    def chosen(self) -> list[str]:
        return [c for c in self._choices if c in self._chosen]

    def _light_row(self) -> None:
        with ui.row().classes("items-center w-full no-wrap gap-2"):
            ui.switch("Light up on my model while the mouse is on a name", value=self._lighting,
                      on_change=lambda e: self._switch_light(e.value)).props("dense") \
                .tooltip("Shows on stream too. It takes the tint away that the part had before")
            ui.space()
            with ui.button(icon="palette").props("flat round dense").style(f"color: {self._color[:7]}") \
                    .tooltip("The colour it lights up in") as button:
                picker = ui.color_picker(on_pick=lambda e: self._light_color(e.color, button))
                picker.q_color.props("format-model=hex")
                picker.set_color(self._color)

    async def _switch_light(self, on: bool) -> None:
        self._lighting = on
        app.storage.general[LIGHT_KEY] = on
        if not on:
            await self._point("", force=True)

    def _light_color(self, color: str, button: ui.button) -> None:
        self._color = color.upper()
        app.storage.general[LIGHT_COLOR_KEY] = self._color
        button.style(f"color: {color[:7]}")

    def _row(self, choice: str) -> None:
        on = choice in self._chosen
        with ui.row().classes("w-full no-wrap items-center gap-2 rounded px-2 py-0.5 cursor-pointer "
                              "hover:bg-gray-500/15" + (f" {CHOSEN}" if on else "")) as row:
            icon = ui.icon(ON if on else OFF).classes("text-lg text-primary")
            ui.label(choice).classes("text-sm break-all")
        self._rows[choice] = (row, icon)
        row.on("mousedown", lambda c=choice: self._start(c))
        row.on("mouseenter", lambda e, c=choice: self._entered(c, e.args.get("buttons") == 1), args=["buttons"])

    async def _entered(self, choice: str, held: bool) -> None:
        if held:  # the left button is held, so this row is part of a stroke
            self._set(choice, self._paint)
        await self._point(choice)

    async def _point(self, choice: str, force: bool = False) -> None:
        """Lights `choice` up in the program ("" = nothing). Rows the mouse crossed while the program was
        busy are skipped: only the newest is sent."""
        if self._light is None or not (self._lighting or force):
            return
        self._wanted = choice
        if self._busy:
            return
        self._busy = True
        try:
            while self._lit != self._wanted:
                target = self._wanted
                await self._light(target, self._color)
                self._lit = target
        except Exception as e:  # the program isn't connected: say it once and stop trying
            self._lighting = False
            ui.notify(f"Can't light it up: {e}", type="warning")
        finally:
            self._busy = False

    def _start(self, choice: str) -> None:
        self._paint = choice not in self._chosen
        self._set(choice, self._paint)

    def _set(self, choice: str, on: bool) -> None:
        if (choice in self._chosen) == on:
            return
        (self._chosen.add if on else self._chosen.discard)(choice)
        row, icon = self._rows[choice]
        icon.set_name(ON if on else OFF)
        row.classes(add=CHOSEN) if on else row.classes(remove=CHOSEN)
        self._counted()

    def _all(self, on: bool) -> None:
        for choice, (row, _) in self._rows.items():
            if row.visible:
                self._set(choice, on)

    def _show(self, search: str) -> None:
        words = search.casefold().split()
        for choice, (row, _) in self._rows.items():
            row.set_visibility(all(word in choice.casefold() for word in words))

    def _counted(self) -> None:
        self._count.set_text(f"{len(self._chosen)} of {len(self._choices)} ticked")
