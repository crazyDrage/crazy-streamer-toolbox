from pathlib import Path
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.connections.obs.fit_media_by_orientation import FitMediaByOrientation
from streamer_toolbox.core.config.fit_target_config import FitTargetConfig
from streamer_toolbox.core.layout.orientation_layout_policy import OrientationLayoutPolicy
from streamer_toolbox.core.interfaces.video_probe import VideoProbe
from streamer_toolbox.core.interfaces.scene_item_editor import SceneItemEditor


def add_fit_actions(actions: ActionRegistry, targets: tuple[FitTargetConfig, ...], probe: VideoProbe,
                    editor: SceneItemEditor) -> None:
    """Register obs.fit_<target>(video_path) for every [obs.fit.<target>] in the config."""
    for target in targets:
        fitter = FitMediaByOrientation(probe, OrientationLayoutPolicy(target.landscape, target.portrait),
                                       editor, target.source, list(target.scenes))
        actions.add(f"obs.fit_{target.name}", _handler(fitter),
                    f"Resizes {target.source} for landscape or portrait video", group="Sources")


def _handler(fitter: FitMediaByOrientation):
    async def fit(video_path: str) -> dict[str, Any]:
        bounds = await fitter.fit(Path(video_path))
        if bounds is None:
            return {"fitted": False, "reason": "video size unknown"}
        return {"fitted": True, "x": bounds.x, "y": bounds.y, "width": bounds.width, "height": bounds.height}
    return fit
