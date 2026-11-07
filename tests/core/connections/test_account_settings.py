import unittest

from streamer_toolbox.core.connections.account_settings import ACCOUNT_DEFAULTS, AccountSettings


class TestAccountSettings(unittest.TestCase):
    """The account settings every streaming platform's connection shares (his ask of 2026-11-06)."""

    def setUp(self) -> None:
        self.settings = dict(ACCOUNT_DEFAULTS)
        self.accounts = AccountSettings(lambda: self.settings, self.settings.update)

    def test_bots_and_listening(self) -> None:
        self.accounts.set_bot("drage_bot", True)
        self.accounts.set_listening("second", True)
        self.accounts.set_listening("drage_bot", True)  # a bot never listens, even when the list says so
        self.assertTrue(self.accounts.is_bot("drage_bot"))
        self.assertTrue(self.accounts.listens("main", "main"))
        self.assertEqual(self.accounts.listening("main", ["main", "second", "drage_bot", "third"]),
                         ["main", "second"])
        self.assertEqual(self.accounts.listening("main", ["second"]), ["second"])  # the main one isn't usable now

    def test_a_removed_account_is_forgotten(self) -> None:
        self.accounts.set_bot("drage_bot", True)
        self.accounts.set_listening("drage_bot", True)
        self.accounts.forget("drage_bot")
        self.assertEqual((self.settings["bot_accounts"], self.settings["listen"]), ([], []))

    def test_the_switch(self) -> None:
        self.assertFalse(self.accounts.multiple)
        self.accounts.set_multiple(True)
        self.assertTrue(self.accounts.multiple)


if __name__ == "__main__":
    unittest.main()
