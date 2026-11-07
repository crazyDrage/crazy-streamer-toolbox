from collections.abc import Callable

from streamer_toolbox.core.upgrades.settings_upgrade import SettingsUpgrade


class RumbleAccountsUpgrade(SettingsUpgrade):
    """Settings version 4 (2026-11-06, docs/SETTINGS_CHANGES.md): the Rumble address moves into the accounts folder
    (config/secrets/rumble/rumble.txt) and becomes the main account ([rumble] main_account); Connect (or the
    first start) renames it after the name Rumble gives it. His "the multi account option should be possible for
    every streaming platform". Flows don't change.

    `move_rumble_address()` does the move (AccountKeys.move_single_file) and gives the account's name, "" when
    there was no address."""

    version = 4
    about = "Rumble accounts"

    def __init__(self, move_rumble_address: Callable[[], str]) -> None:
        self._move_rumble_address = move_rumble_address

    def run(self) -> list[str]:
        name = self._move_rumble_address()
        return [f"the Rumble address moved to secrets/rumble/{name}.txt, {name} is the main account"] if name else []
