import unittest

from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.role_match import roles_match, roles_of, roles_text

ROLES = ("viewer", "sub", "vip", "mod", "broadcaster")


class TestRoleMatch(unittest.TestCase):
    def _fires(self, match: dict) -> list[bool]:
        trigger = FlowTrigger("redeem", match)
        return [trigger.matches("redeem", {"role": role}) for role in ROLES]

    def test_the_ticked_roles_start_it_and_no_others(self) -> None:
        self.assertEqual(roles_match(["mod", "vip"]), {"roles": "vip, mod"})  # lowest first, whatever the order
        self.assertEqual(self._fires(roles_match(["vip", "mod"])), [False, False, True, True, False])
        self.assertEqual(self._fires(roles_match(["viewer", "sub", "vip"])), [True, True, True, False, False])
        self.assertEqual(self._fires(roles_match(["sub", "broadcaster"])), [False, True, False, False, True])
        self.assertEqual(self._fires({"roles": "Mod , VIP"}), [False, False, True, True, False])  # typed by hand
        self.assertTrue(FlowTrigger("redeem", roles_match(["viewer"])).matches("redeem", {}))  # no role known

    def test_all_ticked_or_none_is_everyone(self) -> None:
        for ticked in (ROLES, ()):
            self.assertEqual(roles_match(ticked), {})
            self.assertEqual(roles_text(ticked), "Everyone")
        self.assertEqual(roles_of({"reward": "Lizard"}), list(ROLES))
        self.assertEqual(self._fires({}), [True] * 5)

    def test_what_the_button_says_and_the_round_trip(self) -> None:
        self.assertEqual(roles_text(["mod", "vip"]), "VIPs, Mods")
        self.assertEqual(roles_text(["broadcaster"]), "You")
        for ticked in (["viewer"], ["sub", "mod"], ["viewer", "sub", "vip", "mod"]):
            self.assertEqual(roles_of(roles_match(ticked)), ticked)

    def test_the_older_and_up_and_down_keys_still_work_and_show_as_ticks(self) -> None:
        self.assertEqual(self._fires({"who": "vip"}), [False, False, True, True, True])
        self.assertEqual(self._fires({"who_max": "vip"}), [True, True, True, False, False])
        self.assertEqual(roles_of({"who": "mod"}), ["mod", "broadcaster"])
        self.assertEqual(roles_of({"who_max": "sub"}), ["viewer", "sub"])
        self.assertEqual(roles_of({"who": "sub", "who_max": "vip"}), ["sub", "vip"])


if __name__ == "__main__":
    unittest.main()
