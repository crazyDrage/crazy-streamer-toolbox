import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.points.local_point_bank import LocalPointBank
from streamer_toolbox.core.points.point_actions import PointActions
from streamer_toolbox.core.points.point_earner import PointEarner
from streamer_toolbox.core.points.point_rules import PointRules
from streamer_toolbox.core.points.point_store import PointStore


class TestPoints(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.path = Path(self._dir.name) / "points" / "points.json"
        self.store = PointStore(self.path)
        self.said: list[tuple[str, str]] = []

        async def say(platform: str, text: str) -> None:
            self.said.append((platform, text))

        self.say = say

    def tearDown(self) -> None:
        self._dir.cleanup()

    def earner(self, **rules) -> PointEarner:
        return PointEarner(self.store, PointRules.from_dict({"enabled": True, **rules}), say=self.say)

    def test_a_viewer_is_a_name_on_a_platform_and_points_dont_go_below_zero(self) -> None:
        self.assertEqual(self.store.add("VexFan", 30), 30)
        self.assertEqual(self.store.add("@vexfan", 5), 35)  # one viewer, however it's written
        self.assertEqual(self.store.add("vexfan", 7, "YouTube"), 7)  # another one on YouTube
        self.assertEqual(self.store.add("VexFan", -100), 0)
        self.assertEqual(self.store.set("Kit", 12), 12)
        self.assertFalse(self.store.spend("Kit", 13))
        self.assertTrue(self.store.spend("Kit", 2))
        self.assertEqual(self.store.top(2), [{"user": "Kit", "platform": "twitch", "points": 10},
                                             {"user": "vexfan", "platform": "youtube", "points": 7}])
        self.assertEqual(len(PointStore(self.path).all()), 3)  # kept in the file
        self.store.remove("vexfan", "youtube")
        self.assertEqual(PointStore(self.path).get("vexfan", "youtube"), 0)
        with self.assertRaises(ValueError):
            self.store.add(" ", 1)

    def test_the_rules_come_from_the_settings_and_forgive_odd_values(self) -> None:
        rules = PointRules.from_dict({"enabled": "true", "per_time": "25", "minutes": 0, "on_sub": "many",
                                      "name": " rats ", "unknown": 1})
        self.assertEqual((rules.enabled, rules.per_time, rules.minutes, rules.on_sub, rules.name),
                         (True, 25, 1, 500, "rats"))
        self.assertFalse(PointRules.from_dict({}).enabled)
        self.assertEqual(PointRules.from_dict(rules.to_dict()), rules)

    async def test_chatters_are_paid_and_only_while_live(self) -> None:
        earner = self.earner(per_time=10)
        await earner.handle("twitch.chat", {"user": "Kit", "user_login": "kit", "platform": "twitch"})
        await earner.handle("twitch.chat", {"user": "Kit", "user_login": "kit", "platform": "twitch"})
        await earner.handle("youtube.chat", {"user": "Ann", "platform": "youtube"})
        self.assertEqual(await earner.pay(), 2)
        self.assertEqual((self.store.get("kit"), self.store.get("Ann", "youtube")), (10, 10))
        self.assertEqual(await earner.pay(), 0)  # nobody wrote since
        await earner.handle("twitch.offline", {"platform": "twitch"})
        await earner.handle("twitch.chat", {"user": "Kit", "user_login": "kit", "platform": "twitch"})
        self.assertEqual(await earner.pay(), 0)  # the stream is over
        await earner.handle("twitch.online", {"platform": "twitch"})
        await earner.handle("twitch.chat", {"user": "Kit", "user_login": "kit", "platform": "twitch"})
        self.assertEqual((await earner.pay(), self.store.get("kit")), (1, 20))

    async def test_lurkers_earn_too_when_twitch_lists_them_and_the_stream_is_on(self) -> None:
        live = {"on": True}

        async def viewers() -> list[str]:
            return ["kit", "lurker"]

        async def is_live() -> bool:
            return live["on"]

        earner = PointEarner(self.store, PointRules.from_dict({"enabled": True, "per_time": 10}), say=self.say,
                             viewers=viewers, live=is_live)
        await earner.handle("twitch.chat", {"user": "Kit", "user_login": "kit", "platform": "twitch"})
        self.assertEqual(await earner.pay(), 2)  # the one who wrote isn't paid twice
        self.assertEqual((self.store.get("kit"), self.store.get("lurker")), (10, 10))
        live["on"] = False  # people sit in an offline chat: no points for that
        self.assertEqual((await earner.pay(), self.store.get("lurker")), (0, 10))

        async def refused() -> list[str]:
            raise PermissionError("press Connect once")

        earner = PointEarner(self.store, PointRules.from_dict({"enabled": True}), viewers=refused)
        await earner.handle("twitch.chat", {"user": "Kit", "user_login": "kit", "platform": "twitch"})
        self.assertEqual(await earner.pay(), 1)  # the writers are still paid
        self.assertEqual(earner.lurkers_note, "press Connect once")
        off = PointEarner(self.store, PointRules.from_dict({"enabled": True, "lurkers": False}), viewers=viewers)
        self.assertEqual(await off.pay(), 0)

    async def test_bots_and_the_streamer_dont_earn(self) -> None:
        async def viewers() -> list[str]:
            return ["kit", "nightbot", "dragon", "mybot"]

        def earner(**rules) -> PointEarner:
            return PointEarner(self.store, PointRules.from_dict({"enabled": True, "only_live": False, **rules}),
                               viewers=viewers, own=lambda: "Dragon")

        first = earner()
        for name in ("Nightbot", "Dragon", "Kit"):
            await first.handle("twitch.chat", {"user": name, "user_login": name.casefold(), "platform": "twitch"})
            await first.handle("twitch.follow", {"user": name, "user_login": name.casefold(), "platform": "twitch"})
        self.assertEqual(await first.pay(), 2)  # kit and mybot
        self.assertEqual([self.store.get(name) for name in ("kit", "mybot", "nightbot", "dragon")], [60, 10, 0, 0])
        second = earner(never="MyBot, @kit", streamer_earns=True)
        self.assertEqual(await second.pay(), 2)  # his own list replaces the bots; he earns now
        self.assertEqual([self.store.get(name) for name in ("kit", "mybot", "nightbot", "dragon")], [60, 10, 10, 10])

    async def test_bonuses_and_the_points_command(self) -> None:
        earner = self.earner(name="rats", on_follow=50, on_sub=500, on_raid=100, per_100_bits=100)
        for kind, data in (("twitch.follow", {"user": "Kit", "user_login": "kit"}),
                           ("twitch.sub", {"user": "Kit", "user_login": "kit"}),
                           ("twitch.cheer", {"user": "Kit", "user_login": "kit", "bits": 250}),
                           ("twitch.raid", {"user": "Vex", "user_login": "vex", "viewers": 9}),
                           ("twitch.gift", {"user": "", "user_login": "", "amount": 5})):
            await earner.handle(kind, {**data, "platform": "twitch"})
        self.assertEqual((self.store.get("kit"), self.store.get("vex")), (800, 100))
        await earner.handle("twitch.chat", {"user": "Kit", "user_login": "kit", "command": "!points",
                                            "platform": "twitch"})
        self.assertEqual(self.said, [("twitch", "Kit has 800 rats")])
        off = PointEarner(self.store, PointRules(), say=self.say)  # switched off: nothing is given
        await off.handle("twitch.follow", {"user": "New", "user_login": "new", "platform": "twitch"})
        self.assertEqual(self.store.get("new"), 0)

    async def test_the_boxes(self) -> None:
        actions = ActionRegistry()
        bank = LocalPointBank(self.store)
        PointActions(lambda: bank).add_to(actions)
        self.assertEqual(await actions.run("points.add", viewer="Kit", amount="40"), 40)
        self.assertEqual(await actions.run("points.spend", viewer="kit", amount=15), {"ok": True, "points": 25})
        self.assertEqual(await actions.run("points.spend", viewer="kit", amount=99), {"ok": False, "points": 25})
        self.assertEqual(await actions.run("points.give", giver="kit", receiver="Vex", amount=5),
                         {"giver": 20, "receiver": 5})
        with self.assertRaises(ValueError):
            await actions.run("points.give", giver="vex", receiver="kit", amount=50)
        self.assertEqual(await actions.run("points.get", viewer="vex"), 5)
        self.assertEqual(await actions.run("points.set", viewer="vex", points=3), 3)
        self.assertEqual([one["user"] for one in await actions.run("points.top", count=1)], ["Kit"])
        with self.assertRaises(ValueError):
            await actions.run("points.add", viewer="", amount=1)


if __name__ == "__main__":
    unittest.main()
