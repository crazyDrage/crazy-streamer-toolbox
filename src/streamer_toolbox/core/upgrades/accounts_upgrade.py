from collections.abc import Callable

from streamer_toolbox.core.config.config_table_writer import ConfigTableWriter
from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.upgrades.settings_upgrade import SettingsUpgrade

# other names a default event type got after it shipped (2026-11-05: a chatter's deleted messages)
NEW_NAMES: dict[str, tuple[str, ...]] = {"chat_deleted": ("delete-messages",)}
# the fields of a Twitch app of his own: gone (his "we don't need a custom one anymore", 2026-11-05)
OWN_APP = ("client_id", "client_secret", "redirect_url")


class AccountsUpgrade(SettingsUpgrade):
    """Settings version 2 (2026-11-05, docs/SETTINGS_CHANGES.md): the Twitch login moves into the accounts folder
    (config/secrets/twitch/<login>.json) and becomes the main account ([twitch] main_account, his plan
    docs/PLAN_multi_accounts.md); the event type chat_deleted also hears delete-messages; the Twitch app of his
    own (client_id, client_secret, redirect_url in [twitch]) is taken out: only the toolbox's own app logs in now.
    Flows don't change.

    `move_twitch_login()` does the move (AccountTokens.move_single_file) and gives the account's name, "" when
    there was no login."""

    version = 2
    about = "Twitch accounts"

    def __init__(self, move_twitch_login: Callable[[], str], events: EventTypeStore,
                 config: ConfigTableWriter) -> None:
        self._move_twitch_login = move_twitch_login
        self._events = events
        self._config = config

    def run(self) -> list[str]:
        said = []
        name = self._move_twitch_login()
        if name:
            said.append(f"the Twitch login moved to secrets/twitch/{name}.json, {name} is the main account")
        for event, names in NEW_NAMES.items():
            for added in self._events.add_other_names(event, names):
                said.append(f"event {event} also hears {added}")
        removed = self._config.remove("twitch", OWN_APP)
        if removed:
            said.append(f"Twitch: {', '.join(removed)} are gone (only the toolbox's own app logs in now)")
        if str(removed.get("client_id") or "").strip():
            said.append("Twitch: the login came from your own app, press Connect once to log in with the toolbox's")
        return said
