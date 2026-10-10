from nicegui import ui

from streamer_toolbox.core.actions.action_registry import ActionRegistry


class OverlaySource:
    """Puts an overlay page into OBS as a Browser source: as big as the canvas, its sound through OBS's mixer.
    Uses the OBS boxes (Create source, Raw request), so it works exactly when they do."""

    def __init__(self, actions: ActionRegistry) -> None:
        self._actions = actions

    async def scenes(self) -> list[str]:
        """OBS's scenes; empty if OBS is off or not there (the scene can still be typed)."""
        try:
            return list(await self._actions.get("obs.create_source").options["scene"]())
        except Exception:
            return []

    async def add(self, scene: str | None, name: str, address: str) -> bool:
        """Makes the Browser source `name` in the scene and says how it went; True if it's there now."""
        if not scene:
            ui.notify("Pick the scene first", type="warning")
            return False
        try:
            video = await self._actions.run("obs.request", request="GetVideoSettings")
            await self._actions.run("obs.create_source", scene=scene, name=name, kind="browser_source",
                                    settings={"url": address, "width": video["baseWidth"],
                                              "height": video["baseHeight"], "reroute_audio": True})
        except Exception as e:
            hint = f" If '{name}' is there already: in OBS, Add Existing puts it into another scene." \
                if "exist" in str(e).casefold() else ""
            ui.notify(f"{e}{hint}", type="negative", multi_line=True)
            return False
        ui.notify(f"'{name}' is in {scene} now", type="positive")
        return True

    async def ask_and_add(self, name: str, address: str) -> None:
        """A small window that asks for the scene, then adds the source."""
        with ui.dialog() as dialog, ui.card().classes("w-96 gap-3"):
            ui.label("Add it to OBS").classes("text-lg font-semibold")
            ui.label(f"Makes the Browser source '{name}' in a scene, as big as your canvas.") \
                .classes("text-sm opacity-80")
            scene = ui.select(await self.scenes(), label="Scene", new_value_mode="add-unique") \
                .props("outlined dense options-dense").classes("w-full")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat no-caps")
                ui.button("Add", on_click=lambda: dialog.submit(scene.value)).props("unelevated no-caps")
        picked = await dialog
        dialog.delete()
        if picked:
            await self.add(picked, name, address)
