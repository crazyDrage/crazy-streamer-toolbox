import unittest

from streamer_toolbox.core.events.role_book import RoleBook
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger


def chat(user_id: str, role: str, platform: str = "twitch") -> dict:
    return {"user": f"User{user_id}", "user_login": f"user{user_id}", "user_id": user_id, "role": role,
            "message": "hi", "platform": platform}


def redeem(user_id: str) -> dict:
    return {"user": f"User{user_id}", "user_login": f"user{user_id}", "user_id": user_id, "reward": "Lizard",
            "platform": "twitch"}


class TestRoleBook(unittest.TestCase):
    def test_a_redeem_gets_the_role_of_the_viewers_last_chat_message(self) -> None:
        book = RoleBook()
        self.assertEqual(book.fill("twitch.redeem", redeem("7"))["role"], "viewer")  # never wrote: plain viewer
        book.fill("twitch.chat", chat("7", "mod"))
        self.assertEqual(book.fill("twitch.redeem", redeem("7"))["role"], "mod")
        self.assertEqual(book.fill("redeem", {**redeem("7"), "source": "twitch.redeem"})["role"], "mod")
        book.fill("twitch.chat", chat("7", "vip"))  # no mod anymore
        self.assertEqual(book.fill("twitch.redeem", redeem("7"))["role"], "vip")
        self.assertEqual(book.fill("twitch.redeem", redeem("8"))["role"], "viewer")

    def test_a_chat_message_and_other_events_stay_as_they_are(self) -> None:
        book = RoleBook()
        message = chat("7", "sub")
        self.assertIs(book.fill("twitch.chat", message), message)
        tick = {"every": 10}
        self.assertIs(book.fill("timer", tick), tick)
        hit = {"item": "apple"}
        self.assertIs(book.fill("tits.hit", hit), hit)

    def test_platforms_are_kept_apart_and_a_name_is_enough(self) -> None:
        book = RoleBook()
        book.fill("youtube.chat", {"user": "Ann", "role": "mod", "user_id": "c1", "platform": "youtube"})
        self.assertEqual(book.fill("youtube.superchat", {"user": "ann", "platform": "youtube"})["role"], "mod")
        self.assertEqual(book.fill("rumble.rant", {"user": "Ann", "platform": "rumble"})["role"], "viewer")

    def test_who_just_subbed_is_at_least_a_sub_and_the_streamer_is_the_streamer(self) -> None:
        book = RoleBook(lambda: "1")
        self.assertEqual(book.fill("twitch.sub", redeem("7"))["role"], "sub")
        self.assertEqual(book.fill("twitch.raid", redeem("7"))["role"], "viewer")
        book.fill("twitch.chat", chat("7", "mod"))
        self.assertEqual(book.fill("twitch.resub", redeem("7"))["role"], "mod")
        self.assertEqual(book.fill("twitch.redeem", redeem("1"))["role"], "broadcaster")

    def test_a_trigger_for_mods_and_one_for_everyone_else(self) -> None:
        book = RoleBook()
        book.fill("twitch.chat", chat("7", "mod"))
        mods = FlowTrigger("twitch.redeem", {"reward": "Lizard", "who": "mod"})
        others = FlowTrigger("twitch.redeem", {"reward": "Lizard", "roles": "viewer, sub, vip"})
        by_mod, by_viewer = book.fill("twitch.redeem", redeem("7")), book.fill("twitch.redeem", redeem("8"))
        self.assertEqual([t.matches("twitch.redeem", by_mod) for t in (mods, others)], [True, False])
        self.assertEqual([t.matches("twitch.redeem", by_viewer) for t in (mods, others)], [False, True])


if __name__ == "__main__":
    unittest.main()
