from dataclasses import dataclass, field

from streamer_toolbox.core.config.fit_target_config import FitTargetConfig


@dataclass(frozen=True)
class ObsConfig:
    """The [obs] table. Off by default: the toolbox connects to OBS when it starts only with enabled = true."""

    enabled: bool = False
    url: str = "ws://127.0.0.1:4455"
    password: str = ""
    fit_targets: tuple[FitTargetConfig, ...] = field(default_factory=tuple)
