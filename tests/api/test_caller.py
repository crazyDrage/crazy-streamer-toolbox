import unittest

from streamer_toolbox.api.caller import Caller


class TestCaller(unittest.TestCase):
    def test_patterns_and_exact_names(self) -> None:
        caller = Caller("kit", ("hello.*", "obs.fit_raid_clip"), token="x")
        self.assertTrue(caller.may_run("hello.greet"))
        self.assertTrue(caller.may_run("obs.fit_raid_clip"))
        self.assertFalse(caller.may_run("obs.fit_sound_alert"))

    def test_empty_allowlist_allows_nothing(self) -> None:
        self.assertFalse(Caller("nobody", (), token="x").may_run("hello.greet"))


if __name__ == "__main__":
    unittest.main()
