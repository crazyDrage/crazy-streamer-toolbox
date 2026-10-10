import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.connections.twitch.twitch_api_error import TwitchApiError
from streamer_toolbox.core.widgets.channel_lookup import ChannelLookup
from streamer_toolbox.core.widgets.kept_answers import KeptAnswers
from tests.fakes.fake_helix import FakeHelix

USERS = [{"id": "42", "login": "dragon", "display_name": "Dragon", "profile_image_url": "https://pic/dragon.png"},
         {"id": "77", "login": "kit", "display_name": "Kit", "profile_image_url": "https://pic/kit.png",
          "broadcaster_type": "affiliate"},
         {"id": "900", "login": "12345", "display_name": "12345", "profile_image_url": ""}]
OWN = {"username": "dragon", "providerId": "42", "id": "se1abc"}


def users(params: dict) -> dict:
    return {"data": [u for u in USERS if u["id"] == params.get("id") or u["login"] == params.get("login")]}


class TestChannelLookup(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.helix = FakeHelix({("GET", "users"): users})
        self.now = 0.0
        self.lookup = ChannelLookup(self.helix, lambda: OWN)
        self.kept = self._kept()

    def _kept(self, path: Path | None = None, keep_count: int = 500) -> KeptAnswers:
        return KeptAnswers(path, keep_count, keep_seconds=60, clock=lambda: self.now)

    async def test_a_channel_by_name_in_streamelements_shape(self) -> None:
        self.assertEqual(await self.lookup.channel("#Kit", self.kept), {
            "_id": "77", "provider": "twitch", "providerId": "77", "username": "kit", "alias": "kit",
            "displayName": "Kit", "avatar": "https://pic/kit.png", "broadcasterType": "affiliate",
            "isPartner": False, "inactive": False, "suspended": False, "profile": {"title": "Kit's profile"}})
        self.assertEqual(self.helix.sent("GET", "users"), [({"login": "kit"}, {})])

    async def test_his_own_channel_by_name_twitch_id_or_streamelements_id(self) -> None:
        for who in ("dragon", "42", "SE1ABC"):
            answer = await self.lookup.channel(who, self.kept)
            self.assertEqual((answer["_id"], answer["providerId"], answer["avatar"]),
                             ("se1abc", "42", "https://pic/dragon.png"), who)
        self.assertEqual((await self.lookup.channel("12345", self.kept))["providerId"], "900")  # a name made of digits

    async def test_answers_are_kept_for_a_while(self) -> None:
        await self.lookup.channel("kit", self.kept)
        await self.lookup.channel("kit", self.kept)
        await self.lookup.channel("nobody", self.kept)
        await self.lookup.channel("nobody", self.kept)  # "not there" is kept too
        self.assertEqual(len(self.helix.calls), 2)
        self.now = 61
        await self.lookup.channel("kit", self.kept)
        self.assertEqual(len(self.helix.calls), 3)

    async def test_answers_are_kept_on_the_disk_and_not_without_end(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "cache" / "widget_channels.json"
            first = self._kept(path, 2)
            await self.lookup.channel("kit", first)
            await self.lookup.channel("nobody", first)
            again = self._kept(path, 2)  # as after a restart
            self.assertEqual((await self.lookup.channel("kit", again))["avatar"], "https://pic/kit.png")
            self.assertIsNone(await self.lookup.channel("nobody", again))
            self.assertEqual(len(self.helix.calls), 2)  # Twitch wasn't asked again
            await self.lookup.channel("dragon", again)  # a third one: the oldest (kit) goes
            self.assertEqual(len(self.helix.calls), 3)
            await self.lookup.channel("kit", again)
            self.assertEqual(len(self.helix.calls), 4)
            self.assertEqual(len(self._kept(path)), 2)
            path.write_text("not json", encoding="utf-8")  # a broken file is no loss
            self.assertEqual((await self.lookup.channel("kit", self._kept(path)))["username"], "kit")

    async def test_what_it_cant_say_is_none(self) -> None:
        self.assertIsNone(await self.lookup.channel("nobody", self.kept))
        self.assertIsNone(await self.lookup.channel("", self.kept))
        self.assertIsNone(await self.lookup.channel("../x y", self.kept))  # no Twitch name: Twitch isn't asked
        self.assertEqual(len(self.helix.calls), 1)
        self.helix.answers[("GET", "users")] = TwitchApiError(401, "not logged in")
        self.assertIsNone(await self.lookup.channel("kit", self.kept))
        self.helix.answers[("GET", "users")] = users
        self.assertEqual((await self.lookup.channel("kit", self.kept))["username"], "kit")  # a failure isn't kept


if __name__ == "__main__":
    unittest.main()
