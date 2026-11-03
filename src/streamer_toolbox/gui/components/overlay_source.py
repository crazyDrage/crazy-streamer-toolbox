from nicegui import ui

from streamer_toolbox.connections.obs.obs_request_error import ObsRequestError
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.gui.components.keep_typed import keep_typed

NOT_FOUND = 600  # obs-websocket's ResourceNotFound


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
        """Makes the Browser source `name` in the scene and says how it went; True if it's there now. When it is
        in OBS already (another scene), that same source goes into this scene too (his round 84: OBS refused a
        second one with that name)."""
        if not scene:
            ui.notify("Pick the scene first", type="warning")
            return False
        try:
            kind = await self._kind_of(name)
            if kind is None:
                video = await self._actions.run("obs.request", request="GetVideoSettings")
                await self._actions.run("obs.create_source", scene=scene, name=name, kind="browser_source",
                                        settings={"url": address, "width": video["baseWidth"],
                                                  "height": video["baseHeight"], "reroute_audio": True})
            elif kind != "browser_source":
                ui.notify(f"OBS has a source called '{name}' already, but it isn't a Browser source ({kind}). "
                          f"Rename that one in OBS, then try again.", type="negative", multi_line=True)
                return False
            elif await self._in_scene(scene, name):
                ui.notify(f"'{name}' is in {scene} already", type="info")
                return True
            else:
                await self._actions.run("obs.add_source_to_scenes", source=name, places=scene)
                ui.notify(f"'{name}' was in OBS already: it is in {scene} now too (the same source)",
                          type="positive", multi_line=True)
                return True
        except Exception as e:
            ui.notify(str(e), type="negative", multi_line=True)
            return False
        ui.notify(f"'{name}' is in {scene} now", type="positive")
        return True

    async def _kind_of(self, name: str) -> str | None:
        """The kind of OBS's source with that name, None if there is none."""
        try:
            answer = await self._actions.run("obs.request", request="GetInputSettings", data={"inputName": name})
        except ObsRequestError as e:
            if e.code == NOT_FOUND:  # OBS has no source by that name
                return None
            raise
        return answer.get("inputKind")

    async def _in_scene(self, scene: str, name: str) -> bool:
        try:
            await self._actions.run("obs.request", request="GetSceneItemId",
                                    data={"sceneName": scene, "sourceName": name})
        except Exception:
            return False
        return True

    async def ask_and_add(self, name: str, address: str) -> None:
        """A small window that asks for the scene, then adds the source."""
        with ui.dialog() as dialog, ui.card().classes("w-96 gap-3"):
            ui.label("Add it to OBS").classes("text-lg font-semibold")
            ui.label(f"Makes the Browser source '{name}' in a scene, as big as your canvas.") \
                .classes("text-sm opacity-80")
            scene = keep_typed(ui.select(await self.scenes(), label="Scene", new_value_mode="add-unique")
                               .props("outlined dense options-dense").classes("w-full"))
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat no-caps")
                ui.button("Add", on_click=lambda: dialog.submit(scene.value)).props("unelevated no-caps")
        picked = await dialog
        dialog.delete()
        if picked:
            await self.add(picked, name, address)
