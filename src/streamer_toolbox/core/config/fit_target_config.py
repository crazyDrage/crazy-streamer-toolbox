from dataclasses import dataclass

from streamer_toolbox.core.layout.box import Box


@dataclass(frozen=True)
class FitTargetConfig:
    """One OBS media source that gets fitted to its video: [obs.fit.<name>] in toolbox.toml."""

    name: str
    source: str
    scenes: tuple[str, ...]
    landscape: Box
    portrait: Box
