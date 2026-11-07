from collections.abc import Callable

from streamer_toolbox.core.upgrades.settings_upgrade import SettingsUpgrade


class YouTubeAccountsUpgrade(SettingsUpgrade):
    """Settings version 3 (2026-11-06, docs/SETTINGS_CHANGES.md): the YouTube login moves into the accounts folder
    (config/secrets/youtube/<name>.json) and becomes the main account ([youtube] main_account), like Twitch's in
    version 2 (his "the multi account option should be possible for every streaming platform"). Flows don't change.

    `move_youtube_login()` does the move (AccountTokens.move_single_file) and gives the account's name, "" when
    there was no login."""

    version = 3
    about = "YouTube accounts"

    def __init__(self, move_youtube_login: Callable[[], str]) -> None:
        self._move_youtube_login = move_youtube_login

    def run(self) -> list[str]:
        name = self._move_youtube_login()
        return [f"the YouTube login moved to secrets/youtube/{name}.json, {name} is the main account"] if name else []
