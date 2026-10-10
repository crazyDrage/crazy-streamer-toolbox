import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from streamer_toolbox.api.caller import Caller
from streamer_toolbox.core.config.fit_target_config import FitTargetConfig
from streamer_toolbox.core.config.obs_config import ObsConfig
from streamer_toolbox.core.layout.box import Box

# Without a config file the toolbox behaves as before tokens existed: localhost only, anything local may call.
DEFAULT_CALLERS = (Caller("local", ("*",), local=True),)


@dataclass(frozen=True)
class ToolboxConfig:
    """config/toolbox.toml: where to listen, which plugins to load, who may call what, OBS settings."""

    host: str = "127.0.0.1"
    port: int = 8850
    plugins_enabled: Optional[frozenset[str]] = None  # None = load every plugin found
    callers: tuple[Caller, ...] = DEFAULT_CALLERS
    obs: ObsConfig = field(default_factory=ObsConfig)
    tables: dict[str, Any] = field(default_factory=dict)  # the whole file, for connections to read their [table]

    @classmethod
    def read(cls, path: Path) -> "ToolboxConfig":
        if not path.exists():
            return cls()
        return cls.parse(tomllib.loads(path.read_text(encoding="utf-8")))

    @classmethod
    def parse(cls, data: dict[str, Any]) -> "ToolboxConfig":
        api = data.get("api", {})
        plugins = data.get("plugins", {})
        enabled = plugins.get("enabled")
        callers_data = data.get("callers")
        callers = DEFAULT_CALLERS if callers_data is None else tuple(
            _caller(name, table) for name, table in callers_data.items())
        return cls(
            host=api.get("host", "127.0.0.1"),
            port=int(api.get("port", 8850)),
            plugins_enabled=None if enabled is None else frozenset(enabled),
            callers=callers,
            obs=_obs(data.get("obs", {})),
            tables=data,
        )


def _caller(name: str, table: dict[str, Any]) -> Caller:
    token = table.get("token") or None
    local = bool(table.get("local", False))
    if not token and not local:
        raise ValueError(f"caller {name!r} needs a token or local = true")
    if token and len(token) < 16:
        raise ValueError(f"caller {name!r}: token is too short (use at least 16 characters)")
    return Caller(name, tuple(table.get("allow", [])), token, local)


def _obs(table: dict[str, Any]) -> ObsConfig:
    targets = tuple(
        FitTargetConfig(name, t["source"], tuple(t["scenes"]), Box(*t["landscape"]), Box(*t["portrait"]))
        for name, t in table.get("fit", {}).items())
    return ObsConfig(bool(table.get("enabled", False)), table.get("url", "ws://127.0.0.1:4455"),
                     table.get("password", ""), targets)
