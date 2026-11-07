import json
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.connections.oauth.account_tokens import AccountTokens
from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.connections.oauth.oauth_token_store import OAuthTokenStore
from streamer_toolbox.core.config.config_table_writer import ConfigTableWriter
from streamer_toolbox.core.connections.secrets_folder import SecretsFolder
from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.upgrades.accounts_upgrade import AccountsUpgrade


class TestAccountsUpgrade(unittest.TestCase):
    """Settings version 2 (docs/SETTINGS_CHANGES.md): a settings folder of v0.3.1 gets the Twitch accounts
    folder, chat_deleted's delete-messages and loses the Twitch own-app fields; a second run changes nothing."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        settings = Path(self._dir.name)
        self.secrets = SecretsFolder(settings)
        self.main = ""
        self.tokens = AccountTokens(self.secrets.folder / "twitch", lambda f: self.secrets.path(f"twitch/{f}"),
                                    lambda: self.main, self._set_main)
        self.old = OAuthTokenStore(self.secrets.path("twitch_token.json"))
        self.config = settings / "toolbox.toml"
        self.config.write_text('[twitch]\nenabled = true\nclient_id = ""\nclient_secret = ""\n'
                               'redirect_url = "http://localhost:17563"\n', encoding="utf-8")
        self.events_path = settings / "event_types.json"
        EventTypeStore(self.events_path)
        data = json.loads(self.events_path.read_text(encoding="utf-8"))
        next(t for t in data["types"] if t["name"] == "chat_deleted")["also_known_as"] = ["delete-message"]
        self.events_path.write_text(json.dumps(data), encoding="utf-8")  # as v0.3.1 wrote it

    def _set_main(self, name: str) -> None:
        self.main = name

    def _upgrade(self) -> AccountsUpgrade:
        return AccountsUpgrade(lambda: self.tokens.move_single_file(self.old), EventTypeStore(self.events_path),
                               ConfigTableWriter(self.config))

    def test_a_settings_folder_of_v0_3_1_moves_up(self) -> None:
        self.old.save(OAuthToken("a", "r", 9_999_999_999.0, (), "1", "crazydrage"))

        said = self._upgrade().run()

        self.assertEqual(said, ["the Twitch login moved to secrets/twitch/crazydrage.json, crazydrage is the main "
                                "account", "event chat_deleted also hears delete-messages",
                                "Twitch: client_id, client_secret, redirect_url are gone (only the toolbox's own app "
                                "logs in now)"])
        self.assertEqual(self.config.read_text(encoding="utf-8"), "[twitch]\nenabled = true\n")
        self.assertEqual((self.main, self.tokens.load().user_id), ("crazydrage", "1"))
        self.assertEqual(EventTypeStore(self.events_path).get("chat_deleted").also_known_as,
                         ("delete-message", "delete-messages"))
        self.assertEqual(self._upgrade().run(), [])

    def test_without_a_twitch_login_the_event_and_the_fields_change(self) -> None:
        self.assertEqual(len(self._upgrade().run()), 2)
        self.assertEqual(self.tokens.names(), [])

    def test_a_login_of_his_own_app_is_told_to_connect_once(self) -> None:
        self.config.write_text('[twitch]\nclient_id = "his-app"\nclient_secret = "s"\n', encoding="utf-8")
        said = self._upgrade().run()
        self.assertIn("press Connect once", said[-1])
        self.assertNotIn("his-app", self.config.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
