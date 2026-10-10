from dataclasses import dataclass


@dataclass(frozen=True)
class ObsStatus:
    """What a connection check saw in OBS, so the streamer can tell which setup the toolbox is talking to."""

    obs_version: str
    websocket_version: str
    profile: str
    scene_collection: str
    scenes: tuple[str, ...]
