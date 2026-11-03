import logging
import tomllib
from pathlib import Path

from streamer_toolbox.core.config.config_table_writer import ConfigTableWriter
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.upgrades.settings_upgrade import SettingsUpgrade
from streamer_toolbox.core.upgrades.settings_version import SETTINGS_VERSION, VERSION_KEY

log = logging.getLogger(__name__)
TABLE = "toolbox"


class SettingsUpgrades:
    """The one place that moves the settings folder up to this toolbox's version (his next release plan, part
    3): each SettingsUpgrade newer than the number in toolbox.toml ([toolbox] settings_version, none = 0) runs
    once, in order, and the number is written after each. Settings from a newer toolbox are read as they are
    (nothing is changed or written back) with a warning; an export from a newer toolbox is not imported.

    Reading an older file's shape (a flow's old steps, alerts.json from before round 65) stays in the store that
    reads it: those work on any file, also one copied in by hand."""

    def __init__(self, config: Path, upgrades: list[SettingsUpgrade]) -> None:
        self._config = config
        self._upgrades = sorted(upgrades, key=lambda u: u.version)
        if [u.version for u in self._upgrades] != list(range(1, SETTINGS_VERSION + 1)):
            raise ValueError(f"settings upgrades must be 1 to {SETTINGS_VERSION}, one each")

    @property
    def version(self) -> int:
        """The settings folder's version: the number toolbox.toml has, 0 without one."""
        if not self._config.is_file():
            return 0
        table = tomllib.loads(self._config.read_text(encoding="utf-8")).get(TABLE, {})
        return int(table.get(VERSION_KEY, 0))

    @property
    def newer(self) -> bool:
        """The settings are from a newer toolbox than this one (an older toolbox was started on them)."""
        return self.version > SETTINGS_VERSION

    def run(self) -> list[str]:
        """Runs what the settings still need; what changed, one line each (for the log)."""
        version = self.version
        if self.newer:
            log.warning("settings are from a newer toolbox (version %s, this one knows up to %s): read as they "
                        "are, nothing upgraded", version, SETTINGS_VERSION)
            return []
        said = []
        for upgrade in self._upgrades[version:]:
            said += [f"{upgrade.version} ({upgrade.about}): {line}" for line in upgrade.run()]
            ConfigTableWriter(self._config).save(TABLE, {VERSION_KEY: upgrade.version})
        return said

    def flow(self, flow: Flow, version: int) -> Flow:
        """A flow from an export made at that settings version, as this toolbox has it."""
        if version > SETTINGS_VERSION:
            raise ValueError(f"it was made by a newer toolbox (settings version {version}, this one knows up to "
                             f"{SETTINGS_VERSION}): update this toolbox first")
        for upgrade in self._upgrades[max(version, 0):]:
            flow = upgrade.flow(flow)
        return flow
