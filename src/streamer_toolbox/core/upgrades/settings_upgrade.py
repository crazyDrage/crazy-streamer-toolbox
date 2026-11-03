import abc

from streamer_toolbox.core.flows.flow import Flow


class SettingsUpgrade(abc.ABC):
    """One step from the settings of one version to the next (SettingsUpgrades runs them in order).

    run() changes the settings folder once; flow() changes one flow an older export brings in, the same way
    (as it is when the step doesn't touch flows)."""

    version: int  # the settings version it upgrades to
    about: str  # one line for the log

    @abc.abstractmethod
    def run(self) -> list[str]:
        """Changes what is older in the settings folder; what it changed, one line each. Running it again
        changes nothing."""

    def flow(self, flow: Flow) -> Flow:
        return flow
