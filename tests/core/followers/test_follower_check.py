import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.followers.follower_check import FollowerCheck
from streamer_toolbox.core.followers.seen_followers import SeenFollowers


class TestFollowerCheck(unittest.IsolatedAsyncioTestCase):
    """His failsafe of 2026-11-05: check the newest followers every minute, keep them in a local list."""

    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp())
        self.path = self.folder / "followers" / "twitch_crazydrage.json"
        self.followers: list[dict] = [{"user_id": "2", "user": "Bee"}, {"user_id": "1", "user": "Ann"}]
        self.sent: list[dict] = []

    def check(self, seen: SeenFollowers | None = None) -> FollowerCheck:
        async def newest() -> list[dict]:
            return list(self.followers)

        return FollowerCheck(newest, self.sent.append, seen or SeenFollowers(self.path), lambda: 60)

    async def test_the_first_check_only_fills_the_list_then_new_ones_come_oldest_first(self) -> None:
        check = self.check()
        self.assertEqual(await check.check(), [])
        self.followers = [{"user_id": "4", "user": "Dee"}, {"user_id": "3", "user": "Cat"}, *self.followers]
        await check.check()
        self.assertEqual([f["user"] for f in self.sent], ["Cat", "Dee"])
        await check.check()
        self.assertEqual(len(self.sent), 2)  # never twice

    async def test_a_follow_the_live_event_had_is_not_sent_again_and_the_other_way(self) -> None:
        seen = SeenFollowers(self.path)
        check = self.check(seen)
        await check.check()
        self.assertTrue(seen.fresh("3"))  # the live event came first
        self.followers = [{"user_id": "3", "user": "Cat"}, *self.followers]
        self.assertEqual(await check.check(), [])
        self.followers = [{"user_id": "5", "user": "Eve"}, *self.followers]
        self.assertEqual([f["user"] for f in await check.check()], ["Eve"])
        self.assertFalse(seen.fresh("5"))  # the late live event is dropped

    async def test_a_live_follow_before_the_first_check_doesnt_make_the_old_ones_news(self) -> None:
        seen = SeenFollowers(self.path)
        self.assertTrue(seen.fresh("9"))
        self.assertEqual(await self.check(seen).check(), [])

    async def test_the_list_is_kept_over_a_restart(self) -> None:
        await self.check().check()
        self.followers = [{"user_id": "3", "user": "Cat"}, *self.followers]
        await self.check().check()  # a new toolbox start: the file says what was seen
        self.assertEqual([f["user"] for f in self.sent], ["Cat"])

    def test_only_the_newest_are_kept(self) -> None:
        seen = SeenFollowers(None, keep=2)
        seen.fill(["1", "2", "3"])
        self.assertTrue(seen.fresh("1"))
        self.assertFalse(seen.fresh("3"))

    async def test_zero_seconds_is_off(self) -> None:
        async def newest() -> list[dict]:
            raise AssertionError("asked")

        await FollowerCheck(newest, self.sent.append, SeenFollowers(None), lambda: 0).run()


if __name__ == "__main__":
    unittest.main()
