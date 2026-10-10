from streamer_toolbox.core.layout.box import Box
from streamer_toolbox.core.interfaces.scene_item_editor import SceneItemEditor


class FakeSceneItemEditor(SceneItemEditor):
    """Records set_bounds calls instead of talking to OBS."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Box]] = []

    async def set_bounds(self, scene_name: str, source_name: str, bounds: Box) -> None:
        self.calls.append((scene_name, source_name, bounds))
