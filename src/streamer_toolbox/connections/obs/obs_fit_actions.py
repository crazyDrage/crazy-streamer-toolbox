from streamer_toolbox.connections.obs.boxes.fit_video import FitVideo
from streamer_toolbox.connections.obs.fit_media_by_orientation import FitMediaByOrientation
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.config.fit_target_config import FitTargetConfig
from streamer_toolbox.core.interfaces.scene_item_editor import SceneItemEditor
from streamer_toolbox.core.interfaces.video_probe import VideoProbe
from streamer_toolbox.core.layout.orientation_layout_policy import OrientationLayoutPolicy


def add_fit_actions(actions: ActionRegistry, targets: tuple[FitTargetConfig, ...], probe: VideoProbe,
                    editor: SceneItemEditor) -> None:
    """Register obs.fit_<target>(video_path) for every [obs.fit.<target>] in the config (a FitVideo box each)."""
    for target in targets:
        fitter = FitMediaByOrientation(probe, OrientationLayoutPolicy(target.landscape, target.portrait),
                                       editor, target.source, list(target.scenes))
        actions.add_box(FitVideo(target.name, target.source, fitter), "obs")
