from dataclasses import replace

from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.upgrades.settings_upgrade import SettingsUpgrade


class FakeSettingsUpgrade(SettingsUpgrade):
    """A settings step that only notes it ran, and puts its number on an imported flow's description."""

    about = "fake"

    def __init__(self, version: int, ran: list[int]) -> None:
        self.version = version
        self._ran = ran

    def run(self) -> list[str]:
        self._ran.append(self.version)
        return [f"step {self.version}"]

    def flow(self, flow: Flow) -> Flow:
        return replace(flow, description=f"{flow.description}{self.version}")
