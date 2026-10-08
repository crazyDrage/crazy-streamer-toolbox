from collections.abc import Callable
from typing import Any

from nicegui import ui

from streamer_toolbox.connections.obs.obs_placement import ObsPlacement
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class PlacementDialog:
    """The window that sets up a place in OBS: pick the scene, Show a marker (a coloured, see-through box appears
    in OBS, at the place the box has now if it has one), drag and size it in OBS, then Use this place: the window
    reads where the marker is, removes it and hands the place to the box. Or take the place of a source that is
    in the scene already. Closing or Cancel removes the marker too."""

    def __init__(self, place: ObsPlacement | None, actions: ActionRegistry,
                 on_done: Callable[[ObsPlacement], None], scene: str = "") -> None:
        self._place = place
        self._actions = actions
        self._on_done = on_done
        self._scene = scene or (place.scene if place else "")  # the box's scene, else where it was set up
        self._marker = ""  # the marker source's name while it's out in OBS
        self._dialog: ui.dialog | None = None

    def open(self) -> None:
        with ui.dialog().props("persistent") as self._dialog, ui.card().classes("w-[34rem] max-w-full gap-3"):
            with ui.row().classes("items-center no-wrap w-full"):
                ui.label("Set up the place").classes("text-lg font-semibold flex-1")
                ui.button(icon="close", on_click=self._cancel).props("flat round dense").tooltip("Cancel")
            scene = ui.select([self._scene] if self._scene else [], value=self._scene or None, label="Scene",
                              new_value_mode="add-unique", on_change=lambda e: self._set_scene(e.value or "")) \
                .props("outlined dense options-dense").classes("w-full")
            self._steps()
        self._dialog.open()
        ui.timer(0.1, lambda: self._load_scenes(scene), once=True)

    async def _load_scenes(self, scene: ui.select) -> None:
        try:
            names = await self._actions.get("obs.place_source").options["scene"]()
        except Exception as e:  # OBS not connected: the scene can still be typed
            ui.notify(f"OBS's scene list isn't available: {e}", type="warning", multi_line=True)
            return
        scene.set_options(names + ([self._scene] if self._scene and self._scene not in names else []),
                          value=self._scene or None)

    @ui.refreshable_method
    def _steps(self) -> None:
        ui.label(f"Now: {self._place.text()}" if self._place else "No place yet.").classes("text-sm opacity-80")
        if self._marker:
            ui.label(f"A coloured box is in {self._scene} now. In OBS: drag it where you want it and size it "
                     "by its corners. Then come back here.").classes("text-sm")
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=self._cancel).props("no-caps flat")
                ui.button("Use this place", icon="check", on_click=self._use_marker).props("no-caps unelevated")
            return
        with ui.row().classes("items-center gap-2 w-full"):
            ui.button("Show a marker in OBS", icon="crop_free", on_click=self._show_marker) \
                .props("no-caps unelevated").tooltip("Puts a coloured box into the scene for you to drag and size")
            ui.button("Take it from a source", icon="content_copy", on_click=self._from_source) \
                .props("no-caps outline").tooltip("Uses the spot and size a source in this scene has right now")
        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Close", on_click=self._cancel).props("no-caps flat")

    def _set_scene(self, scene: str) -> None:
        self._scene = scene

    async def _show_marker(self) -> None:
        if not self._scene:
            ui.notify("Pick the scene first", type="warning")
            return
        try:
            made = await self._actions.run("obs.put_place_marker", scene=self._scene,
                                           place=self._place.to_dict() if self._place else "")
        except Exception as e:
            ui.notify(str(e), type="negative", multi_line=True)
            return
        self._marker = made["source"]
        self._steps.refresh()

    async def _use_marker(self) -> None:
        try:
            place = await self._actions.run("obs.take_place_marker", scene=self._scene, source=self._marker)
        except Exception as e:  # e.g. he deleted the marker in OBS
            ui.notify(f"Can't read the marker: {e}", type="negative", multi_line=True)
            self._marker = ""
            self._steps.refresh()
            return
        self._marker = ""
        self._done(place)

    async def _from_source(self) -> None:
        if not self._scene:
            ui.notify("Pick the scene first", type="warning")
            return
        try:
            sources = await self._actions.get("obs.place_source").options["source"]()
        except Exception as e:
            ui.notify(str(e), type="negative", multi_line=True)
            return
        with ui.dialog() as pick, ui.card().classes("w-80 gap-2"):
            ui.label("Which source?").classes("font-semibold")
            ui.select(sources, with_input=True, on_change=lambda e: pick.submit(e.value)) \
                .props("outlined dense options-dense autofocus").classes("w-full")
        source = await pick
        pick.delete()
        if not source:
            return
        try:
            self._done(await self._actions.run("obs.get_source_place", scene=self._scene, source=source))
        except Exception as e:
            ui.notify(str(e), type="negative", multi_line=True)

    def _done(self, place: Any) -> None:
        self._on_done(ObsPlacement.from_value(place))
        self._dialog.close()

    async def _cancel(self) -> None:
        if self._marker:
            try:
                await self._actions.run("obs.take_place_marker", scene=self._scene, source=self._marker, keep=False)
            except Exception:  # already gone in OBS
                pass
            self._marker = ""
        self._dialog.close()
