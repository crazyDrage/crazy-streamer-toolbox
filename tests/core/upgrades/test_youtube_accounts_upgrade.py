import tempfile
import time
import unittest
from pathlib import Path

from streamer_toolbox.connections.oauth.account_tokens import AccountTokens
from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.connections.oauth.oauth_token_store import OAuthTokenStore
from streamer_toolbox.core.connections.account_keys import fit_name
from streamer_toolbox.core.upgrades.youtube_accounts_upgrade import YouTubeAccountsUpgrade


class TestYouTubeAccountsUpgrade(unittest.TestCase):
    """Settings version 3: the one YouTube login becomes the main account in secrets/youtube/."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        secrets = Path(self.tmp.name)
        self.old = OAuthTokenStore(secrets / "youtube_token.json")
        self.settings = {"main_account": ""}
        self.tokens = AccountTokens(secrets / "youtube", lambda file: secrets / "youtube" / file,
                                    lambda: self.settings["main_account"],
                                    lambda name: self.settings.update(main_account=name), fit_name)
        self.upgrade = YouTubeAccountsUpgrade(lambda: self.tokens.move_single_file(self.old))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_the_login_moves_and_is_the_main_account(self) -> None:
        self.old.save(OAuthToken("a", "r", time.time() + 60, ("read",), "UC1", "crazyDrage"))
        said = self.upgrade.run()
        self.assertEqual((self.tokens.names(), self.settings["main_account"]), (["crazydrage"], "crazydrage"))
        self.assertIsNone(self.old.load())
        self.assertEqual(said, ["the YouTube login moved to secrets/youtube/crazydrage.json, crazydrage is the "
                                "main account"])
        self.assertEqual(self.upgrade.version, 3)

    def test_a_title_with_spaces_becomes_a_name(self) -> None:
        self.old.save(OAuthToken("a", "r", time.time() + 60, ("read",), "UC1", "Fake Tuber"))
        self.upgrade.run()
        self.assertEqual(self.tokens.names(), ["fake_tuber"])

    def test_nothing_to_move(self) -> None:
        self.assertEqual(self.upgrade.run(), [])
        self.assertEqual(self.tokens.names(), [])


if __name__ == "__main__":
    unittest.main()
