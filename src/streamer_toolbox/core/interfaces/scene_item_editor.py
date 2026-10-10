from abc import ABC, abstractmethod

from streamer_toolbox.core.layout.box import Box


class SceneItemEditor(ABC):
    """Edits the transform of an existing source in an OBS scene."""

    @abstractmethod
    async def set_bounds(self, scene_name: str, source_name: str, bounds: Box) -> None:
        """Place the source at the box's top-left corner and fit its content inside the box, keeping aspect."""
