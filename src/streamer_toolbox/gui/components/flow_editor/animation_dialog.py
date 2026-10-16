from collections.abc import Callable
from dataclasses import replace

from nicegui import ui

from streamer_toolbox.connections.vtube_studio.vts_animation import VtsAnimation
from streamer_toolbox.connections.vtube_studio.vts_animation_step import VtsAnimationStep
from streamer_toolbox.connections.vtube_studio.vts_position import VtsPosition
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.files.box_value_files import BoxValueFiles
from streamer_toolbox.gui.components.flow_editor.animation_map import AnimationMap

KIND = "vts/animation"  # its folder in config/boxes
FIELDS = (("x", "x", 0.01), ("y", "y", 0.01), ("rotation", "turn °", 1.0), ("size", "size", 1.0))
NUMBER = "dense outlined hide-bottom-space"


class AnimationDialog:
    """The window of a model animation: fixed spots or changes from where the model is (switching calculates the
    steps over), the steps (spot, seconds to get there, wait after), a map of the path, and buttons that use VTS:
    add the model's spot as a step, take it for a step, go to a step, try the whole animation. Save to file / Load
    from file keep animations to use in other boxes. Done hands the animation to the box."""

    def __init__(self, animation: VtsAnimation, actions: ActionRegistry, files: BoxValueFiles,
                 on_done: Callable[[VtsAnimation], None]) -> None:
        self._animation = animation
        self._actions = actions
        self._files = files
        self._on_done = on_done
        self._model: VtsPosition | None = None  # the model's spot when last read (drawn on the map)
        self._file_name = ""
        self._dialog: ui.dialog | None = None
        self._mode: ui.toggle | None = None

    def open(self) -> None:
        with ui.dialog().props("persistent") as self._dialog, ui.card().classes("w-[860px] max-w-[96vw] gap-3"):
            with ui.row().classes("items-center no-wrap w-full"):
                ui.label("Model animation").classes("text-lg font-semibold flex-1")
                ui.button(icon="close", on_click=self._dialog.close).props("flat round dense").tooltip("Cancel")
            ui.label("Move the model in VTube Studio, then Add the model's spot: each spot is a step. Seconds = how "
                     "long the way to that step takes, wait = how long it stays there.").classes("text-xs opacity-70")
            self._mode = ui.toggle({False: "Fixed spots", True: "From where the model is"},
                                   value=self._animation.relative, on_change=self._mode_changed).props("no-caps dense")
            self._base_line()
            with ui.row().classes("w-full gap-4 items-start"):
                with ui.column().classes("w-80 max-w-full gap-1"):
                    self._map()
                with ui.column().classes("flex-1 min-w-[220px] gap-2"):
                    ui.button("Add the model's spot", icon="add_location_alt", on_click=self._add_spot) \
                        .props("no-caps unelevated").tooltip("Reads where the model is in VTS and adds it as a step")
                    try_button = ui.button("Try it", icon="play_arrow").props("no-caps outline") \
                        .tooltip("Plays it in VTS now, then goes back to where the model started")
                    try_button.on_click(lambda: self._try(try_button))
                    with ui.row().classes("gap-2"):
                        ui.button("Save to file", icon="save", on_click=self._save_file).props("no-caps flat dense")
                        ui.button("Load from file", icon="folder_open", on_click=self._load_file) \
                            .props("no-caps flat dense")
            self._steps()
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=self._dialog.close).props("no-caps flat")
                ui.button("Done", icon="check", on_click=self._done).props("no-caps unelevated")
        self._dialog.open()

    # ---- parts ----

    @ui.refreshable_method
    def _base_line(self) -> None:
        if not self._animation.relative:
            return
        base = self._animation.base
        with ui.row().classes("items-center gap-2 text-xs"):
            ui.label(f"Steps are changes from: {_spot(base)}" if base else
                     "Steps are changes from where the model is when it plays. The first spot you add is the "
                     "start.").classes("opacity-70")
            if base:
                ui.button("Measure from the model's spot now", icon="my_location", on_click=self._set_base) \
                    .props("no-caps flat dense size=sm") \
                    .tooltip("Only for adding spots and the map; the steps stay as they are")

    @ui.refreshable_method
    def _map(self) -> None:
        ui.html(AnimationMap.svg(self._animation, self._model), sanitize=False).classes("w-full")
        ui.label("ring = start · dashed green = the model when last read").classes("text-xs opacity-60")

    @ui.refreshable_method
    def _steps(self) -> None:
        steps = self._animation.steps
        if not steps:
            ui.label("No steps yet.").classes("text-sm opacity-70")
            return
        relative = self._animation.relative
        for index, step in enumerate(steps):
            with ui.row().classes("items-center gap-1 w-full"):
                ui.label(str(index + 1)).classes("w-5 text-center font-bold text-primary")
                for key, label, size in FIELDS:
                    ui.number(("+" if relative else "") + label, value=round(getattr(step.position, key), 4),
                              step=size, on_change=lambda e, i=index, k=key: self._set_spot(i, k, e.value)) \
                        .props(NUMBER).classes("w-[76px]")
                ui.number("seconds", value=step.seconds, min=0, step=0.1,
                          on_change=lambda e, i=index: self._set_step(i, seconds=e.value)) \
                    .props(NUMBER).classes("w-[76px]")
                ui.number("wait after", value=step.wait, min=0, step=0.1,
                          on_change=lambda e, i=index: self._set_step(i, wait=e.value)) \
                    .props(NUMBER).classes("w-[76px]")
                with ui.row().classes("gap-0 no-wrap"):
                    _icon("my_location", "Take the model's spot now for this step", lambda i=index: self._take(i))
                    _icon("near_me", "Move the model to this step", lambda i=index: self._go(i))
                    _icon("arrow_upward", "Move up", lambda i=index: self._swap(i, i - 1), disabled=index == 0)
                    _icon("arrow_downward", "Move down", lambda i=index: self._swap(i, i + 1),
                          disabled=index == len(steps) - 1)
                    _icon("delete", "Remove this step", lambda i=index: self._remove(i))

    def _show(self, steps: bool = True) -> None:
        self._map.refresh()
        self._base_line.refresh()
        if steps:
            self._steps.refresh()

    # ---- editing ----

    def _set_steps(self, steps: list[VtsAnimationStep], refresh: bool = True) -> None:
        self._animation = replace(self._animation, steps=tuple(steps))
        self._show(refresh)

    def _set_spot(self, index: int, key: str, value: float | None) -> None:
        steps = list(self._animation.steps)
        steps[index] = replace(steps[index], position=replace(steps[index].position, **{key: float(value or 0)}))
        self._set_steps(steps, refresh=False)  # typing: the field keeps focus, only the map is drawn again

    def _set_step(self, index: int, **times: float | None) -> None:
        steps = list(self._animation.steps)
        steps[index] = replace(steps[index], **{k: max(0.0, float(v or 0)) for k, v in times.items()})
        self._set_steps(steps, refresh=False)

    def _swap(self, a: int, b: int) -> None:
        steps = list(self._animation.steps)
        steps[a], steps[b] = steps[b], steps[a]
        self._set_steps(steps)

    def _remove(self, index: int) -> None:
        steps = list(self._animation.steps)
        del steps[index]
        self._set_steps(steps)

    # ---- with VTS ----

    async def _read_model(self) -> VtsPosition | None:
        try:
            self._model = VtsPosition.from_dict(await self._actions.run("vts.get_model_position"))
        except Exception as e:
            ui.notify(f"Can't read the model: {e}", type="negative")
            return None
        return self._model

    async def _spot_now(self) -> VtsPosition | None:
        """The model's spot as a step: the spot itself, or the change from the base (the first one sets it)."""
        here = await self._read_model()
        if here is None or not self._animation.relative:
            return here
        if self._animation.base is None:
            self._animation = replace(self._animation, base=here)
        return here.minus(self._animation.base)

    async def _add_spot(self) -> None:
        spot = await self._spot_now()
        if spot is not None:
            self._set_steps([*self._animation.steps, VtsAnimationStep(spot)])

    async def _take(self, index: int) -> None:
        spot = await self._spot_now()
        if spot is not None:
            steps = list(self._animation.steps)
            steps[index] = replace(steps[index], position=spot)
            self._set_steps(steps)

    async def _set_base(self) -> None:
        here = await self._read_model()
        if here is not None:
            self._animation = replace(self._animation, base=here)
            self._show(steps=False)

    async def _go(self, index: int) -> None:
        start = self._animation.base
        if self._animation.relative and start is None:
            start = await self._read_model()
            if start is None:
                return
        target = self._animation.target(self._animation.steps[index], start)
        try:
            await self._actions.run("vts.move_model_to", position=target.to_dict(), seconds=0.5)
        except Exception as e:
            ui.notify(f"Can't move the model: {e}", type="negative")

    async def _try(self, button: ui.button) -> None:
        if not self._animation.steps:
            ui.notify("Add a step first", type="warning")
            return
        button.props("loading")
        try:
            await self._actions.run("vts.play_animation", animation=self._animation.to_dict(), back_to_start=True,
                                    back_seconds=0.5)
        except Exception as e:
            ui.notify(f"Can't play it: {e}", type="negative")
        finally:
            button.props(remove="loading")

    # ---- fixed / relative ----

    async def _mode_changed(self, e) -> None:
        relative = bool(e.value)
        if relative == self._animation.relative:  # set back after a cancel, or by Load
            return
        if not self._animation.steps:
            self._animation = VtsAnimation((), relative, None)
            self._show()
            return
        base = await self._ask_base(relative)
        if base is None:
            self._mode.set_value(not relative)  # cancelled: back to how it was
            return
        self._animation = self._animation.as_relative(base) if relative else self._animation.as_fixed(base)
        self._show()

    async def _ask_base(self, relative: bool) -> VtsPosition | None:
        """Which spot the steps are calculated from when switching; None = cancel."""
        choices: dict[str, str] = {}
        if relative:
            question = "Calculate each step as a change from:"
            choices["first"] = "Step 1 (it plays from wherever the model is)"
        else:
            question = "Put the steps on the screen starting from:"
            if self._animation.base:
                choices["base"] = f"Where they were recorded ({_spot(self._animation.base)})"
        choices["model"] = "Where the model is now"
        with ui.dialog() as ask, ui.card().classes("gap-2"):
            ui.label(question).classes("font-semibold")
            for key, text in choices.items():
                ui.button(text, on_click=lambda k=key: ask.submit(k)).props("no-caps outline").classes("w-full")
            ui.button("Cancel", on_click=lambda: ask.submit(None)).props("no-caps flat").classes("self-end")
        answer = await ask
        ask.clear()
        if answer == "first":
            return self._animation.steps[0].position
        if answer == "base":
            return self._animation.base
        if answer == "model":
            return await self._read_model()
        return None

    # ---- files ----

    async def _save_file(self) -> None:
        with ui.dialog() as ask, ui.card().classes("gap-2 w-80"):
            ui.label("Save the animation as").classes("font-semibold")
            name = ui.input("name", value=self._file_name).props("dense outlined autofocus").classes("w-full")
            ui.label("letters, digits and _ · the same name replaces that file").classes("text-xs opacity-60")
            with ui.row().classes("self-end gap-2"):
                ui.button("Cancel", on_click=lambda: ask.submit(None)).props("no-caps flat")
                ui.button("Save", on_click=lambda: ask.submit(name.value)).props("no-caps unelevated")
        chosen = await ask
        ask.clear()
        if not chosen:
            return
        try:
            path = self._files.save(KIND, chosen, self._animation.to_dict())
        except ValueError as e:
            ui.notify(str(e), type="negative")
            return
        self._file_name = path.stem
        ui.notify(f"Saved as {path.stem}", type="positive")

    async def _load_file(self) -> None:
        names = self._files.names(KIND)
        if not names:
            ui.notify("No saved animations yet (Save to file makes one)", type="info")
            return
        with ui.dialog() as ask, ui.card().classes("gap-2 w-80"):
            ui.label("Load an animation").classes("font-semibold")
            pick = ui.select(names, value=names[0], label="saved animation").props("dense outlined").classes("w-full")
            ui.label("It replaces the steps in this window").classes("text-xs opacity-60")
            with ui.row().classes("self-end gap-2"):
                ui.button("Cancel", on_click=lambda: ask.submit(None)).props("no-caps flat")
                ui.button("Load", on_click=lambda: ask.submit(pick.value)).props("no-caps unelevated")
        chosen = await ask
        ask.clear()
        if not chosen:
            return
        try:
            self._animation = VtsAnimation.from_dict(self._files.load(KIND, chosen))
        except (KeyError, TypeError, ValueError) as e:
            ui.notify(f"Can't load {chosen}: {e}", type="negative")
            return
        self._file_name = chosen
        self._mode.set_value(self._animation.relative)
        self._show()

    def _done(self) -> None:
        self._dialog.close()
        self._on_done(self._animation)  # last: the box's field is drawn again (and this window with it)


def _icon(name: str, tip: str, on_click: Callable, disabled: bool = False) -> None:
    button = ui.button(icon=name, on_click=on_click).props("flat round dense size=sm").tooltip(tip)
    if disabled:
        button.disable()


def _spot(position: VtsPosition) -> str:
    return (f"x {position.x:.2f} · y {position.y:.2f} · turn {position.rotation:.0f}° · "
            f"size {position.size:.0f}")
