import abc


class BackupKeeping(abc.ABC):
    """Which zips of a backups folder stay (SettingsBackup.prune): the starter's daily / monthly ones
    (BackupPolicy), the ones made before a settings upgrade (UpgradeBackupPolicy)."""

    @abc.abstractmethod
    def keep(self, made: dict[str, float]) -> set[str]:
        """Of the backups (name → when it was made, seconds), the names to keep."""
