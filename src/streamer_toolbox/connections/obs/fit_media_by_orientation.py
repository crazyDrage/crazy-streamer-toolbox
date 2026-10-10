from pathlib import Path
from typing import Optional

from streamer_toolbox.core.layout.box import Box
from streamer_toolbox.core.interfaces.layout_policy import LayoutPolicy
from streamer_toolbox.core.interfaces.video_probe import VideoProbe
from streamer_toolbox.core.interfaces.scene_item_editor import SceneItemEditor


class FitMediaByOrientation:
    """Resizes one existing OBS media source to suit the video about to play in it.

    Replaces SAMMI's fit_so_video / fit_sound_alert_video: the same source is used for every
    video, and only its bounds change between landscape and portrait.
    """

    def __init__(
        self,
        probe: VideoProbe,
        policy: LayoutPolicy,
        editor: SceneItemEditor,
        source_name: str,
        scene_names: list[str],
    ) -> None:
        self._probe = probe
        self._policy = policy
        self._editor = editor
        self._source_name = source_name
        self._scene_names = scene_names

    async def fit(self, video_path: Path) -> Optional[Box]:
        """Apply the bounds for this video in every scene. Returns them, or None if the size is unknown."""
        size = self._probe.probe(video_path)
        if size is None:
            return None
        bounds = self._policy.bounds_for(size)
        for scene_name in self._scene_names:
            await self._editor.set_bounds(scene_name, self._source_name, bounds)
        return bounds
