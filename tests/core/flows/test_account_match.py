import unittest

from streamer_toolbox.core.events.common_events import common
from streamer_toolbox.core.events.event_fields import EVENT_FIELDS
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger


class TestAccountMatch(unittest.TestCase):
    """His answer 120 (2026-11-05): a Twitch trigger can pick one or more accounts; each event says its account."""

    def _fires(self, match: dict) -> list[bool]:
        trigger = FlowTrigger("twitch.follow", match)
        return [trigger.matches("twitch.follow", {"user": "Kit", "account": account})
                for account in ("crazydrage", "second_channel", "")]

    def test_one_or_more_accounts(self) -> None:
        self.assertEqual(self._fires({"accounts": "second_channel"}), [False, True, False])
        self.assertEqual(self._fires({"accounts": "Crazydrage , second_channel"}), [True, True, False])

    def test_none_picked_is_every_account(self) -> None:
        self.assertEqual(self._fires({}), [True, True, True])
        self.assertEqual(self._fires({"accounts": ""}), [True, True, True])

    def test_main_account_is_whichever_is_main_when_it_comes(self) -> None:
        trigger = FlowTrigger("twitch.chat", {"accounts": "main account"})
        fires = [trigger.matches("twitch.chat", {"account": account, "main_account": main})
                 for account, main in (("crazydrage", "crazydrage"), ("second_channel", "crazydrage"),
                                       ("second_channel", "Second_Channel"), ("", ""))]
        self.assertEqual(fires, [True, False, True, True])  # his ask of 2026-11-05, and answer 122
        # (no account told: a platform without several, so the main one)
        both = FlowTrigger("twitch.chat", {"accounts": "main account, third"})
        self.assertTrue(both.matches("twitch.chat", {"account": "third", "main_account": "crazydrage"}))

    def test_every_twitch_trigger_has_the_account_dot(self) -> None:
        twitch = [kind for kind in EVENT_FIELDS if kind.startswith("twitch.")]
        self.assertTrue(twitch)
        self.assertTrue(all(EVENT_FIELDS[kind][-1] == "account" for kind in twitch))
        self.assertEqual(EVENT_FIELDS["follow"][-1], "account")  # any platform too: a flow can check it

    def test_any_platform_is_the_main_account_unless_all(self) -> None:
        events = [{"account": "crazydrage", "main_account": "crazydrage"},
                  {"account": "second_channel", "main_account": "crazydrage"},
                  {"account": "", "main_account": ""}]  # e.g. a Rumble follow
        main = FlowTrigger("follow", {"user": "*"})
        every = FlowTrigger("follow", {"user": "*", "accounts": "all accounts"})
        self.assertEqual([main.matches("follow", {"user": "Kit", **e}) for e in events], [True, False, True])
        self.assertEqual([every.matches("follow", {"user": "Kit", **e}) for e in events], [True, True, True])
        self.assertFalse(main.matches("chat", events[0]))  # still only its own kind

    def test_common_events_keep_the_account(self) -> None:
        found = common("twitch.follow", {"user": "Kit", "account": "second_channel", "main_account": "crazydrage"})
        self.assertEqual((found["account"], found["main_account"]), ("second_channel", "crazydrage"))
        self.assertEqual(common("rumble.follow", {"user": "Kit"})["account"], "")


if __name__ == "__main__":
    unittest.main()
