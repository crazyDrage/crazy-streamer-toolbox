from dataclasses import dataclass


@dataclass(frozen=True)
class SettingField:
    """One input on a connection's settings tab, stored under `key` in the connection's toml table."""

    key: str
    label: str
    secret: bool = False   # password-style input; never shown again after saving
    hint: str = ""
