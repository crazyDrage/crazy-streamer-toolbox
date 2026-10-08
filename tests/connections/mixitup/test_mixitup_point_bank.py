import unittest

from streamer_toolbox.connections.mixitup.mixitup_point_bank import MixItUpPointBank
from tests.fakes.fake_mixitup_currency import GEMS, RATS, FakeMixItUpCurrency


class TestMixItUpPointBank(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.mixitup = FakeMixItUpCurrency()
        self.currency = ""
        self.bank = MixItUpPointBank(self.mixitup.send, lambda: self.currency)

    async def test_the_points_are_mix_it_ups_currency(self) -> None:
        self.assertEqual(await self.bank.currencies(), ["rats", "Gems"])
        self.assertEqual(await self.bank.get("@kit"), 40)  # no currency named: the first one
        self.assertEqual(await self.bank.add("Kit", 5), 45)
        self.assertEqual(await self.bank.add("Kit", -100), 0)  # never below 0
        self.assertEqual(await self.bank.set("kit", 12), 12)
        self.assertFalse(await self.bank.spend("kit", 13))
        self.assertTrue(await self.bank.spend("kit", 2))
        self.assertEqual(self.mixitup.amounts["u1"], {RATS: 10, GEMS: 1})
        self.assertEqual(await self.bank.get("VexTube", "youtube"), 7)
        self.currency = "gems"
        self.assertEqual(await self.bank.get("kit"), 1)
        self.currency = "gold"
        with self.assertRaises(KeyError):
            await self.bank.get("kit")
        self.currency = ""
        with self.assertRaises(RuntimeError):
            await self.bank.get("nobody")

    async def test_everyone_with_an_amount_for_moving_it_over_and_the_top(self) -> None:
        viewers = await self.bank.viewers()
        self.assertEqual(viewers, [{"user": "Kit", "platform": "twitch", "points": 40},
                                   {"user": "Vex", "platform": "twitch", "points": 7},
                                   {"user": "VexTube", "platform": "youtube", "points": 7}])  # nobody with 0
        self.assertEqual([one["user"] for one in await self.bank.top(2)], ["Kit", "Vex"])


if __name__ == "__main__":
    unittest.main()
