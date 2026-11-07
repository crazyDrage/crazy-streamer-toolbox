import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.connections.oauth.account_tokens import AccountTokens
from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.connections.oauth.oauth_token_store import OAuthTokenStore
from streamer_toolbox.core.connections.secrets_folder import SecretsFolder

PASSWORD = "correct horse battery"


def _token(login: str, user_id: str, access: str = "a") -> OAuthToken:
    return OAuthToken(access, "r", 9_999_999_999.0, ("user:write:chat",), user_id, login)


class TestAccountTokens(unittest.TestCase):
    """His plan of 2026-11-05: one login file per account, named after its Twitch login; one is the main one."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.secrets = SecretsFolder(Path(self._dir.name))
        self.main = ""
        self.tokens = AccountTokens(self.secrets.folder / "twitch", lambda f: self.secrets.path(f"twitch/{f}"),
                                    lambda: self.main, self._set_main)

    def _set_main(self, name: str) -> None:
        self.main = name

    def test_the_one_login_so_far_moves_in_and_is_the_main_account(self) -> None:
        old = OAuthTokenStore(self.secrets.path("twitch_token.json"))
        old.save(_token("crazyDrage", "1"))

        self.assertEqual(self.tokens.move_single_file(old), "crazydrage")

        self.assertEqual(self.main, "crazydrage")
        self.assertEqual(self.tokens.load().user_id, "1")
        self.assertTrue((self.secrets.folder / "twitch" / "crazydrage.json").is_file())
        self.assertFalse((self.secrets.folder / "twitch_token.json").exists())
        self.assertEqual(self.tokens.move_single_file(old), "")  # once

    def test_an_added_account_leaves_the_main_one_alone(self) -> None:
        self.tokens.save(_token("crazydrage", "1"))
        self.assertEqual(self.tokens.save_account(_token("crazydrage_bot", "2")), "crazydrage_bot")
        self.assertEqual((self.main, self.tokens.names()), ("crazydrage", ["crazydrage", "crazydrage_bot"]))
        self.assertEqual(self.tokens.load_account("crazydrage_bot").user_id, "2")
        self.assertEqual(self.tokens.load().user_id, "1")

    def test_connect_as_another_account_makes_it_the_main_one_and_keeps_the_old(self) -> None:
        self.tokens.save(_token("crazydrage", "1"))
        self.tokens.save(_token("second_channel", "3"))
        self.assertEqual(self.main, "second_channel")
        self.assertEqual(self.tokens.names(), ["crazydrage", "second_channel"])

    def test_a_renamed_twitch_account_moves_to_its_new_name_and_stays_main(self) -> None:
        self.tokens.save(_token("crazydrage", "1"))
        self.tokens.save_account(_token("crazy_drage", "1", "renewed"))
        self.assertEqual((self.tokens.names(), self.main), (["crazy_drage"], "crazy_drage"))
        self.assertEqual(self.tokens.load().access_token, "renewed")

    def test_a_main_account_that_is_gone_falls_back_to_the_first_one(self) -> None:
        self.tokens.save_account(_token("bbb", "2"))
        self.tokens.save_account(_token("aaa", "1"))
        self.main = "removed_one"
        self.assertEqual(self.tokens.main_name(), "aaa")
        self.tokens.remove("aaa")
        self.assertEqual(self.tokens.load().login, "bbb")
        self.tokens.clear()
        self.assertEqual((self.tokens.names(), self.tokens.load()), ([], None))

    def test_a_name_that_is_no_twitch_login_is_never_a_file(self) -> None:
        self.tokens.save_account(_token("aaa", "1"))
        self.assertIsNone(self.tokens.load_account("../aaa"))
        self.tokens.remove("../twitch/aaa")
        self.assertEqual(self.tokens.names(), ["aaa"])

    def test_account_files_are_encrypted_with_a_login_also_when_it_is_set_later(self) -> None:
        self.tokens.save_account(_token("aaa", "1", "secret-access"))
        self.secrets.vault.set_login(PASSWORD)
        self.tokens.save_account(_token("bbb", "2", "other-secret"))
        for name, access in (("aaa", "secret-access"), ("bbb", "other-secret")):
            raw = (self.secrets.folder / "twitch" / f"{name}.json").read_bytes()
            self.assertNotIn(access.encode(), raw)
            self.assertEqual(self.tokens.load_account(name).access_token, access)


if __name__ == "__main__":
    unittest.main()
