import asyncio
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.connections.twitch.twitch_api_error import TwitchApiError
from streamer_toolbox.connections.twitch.twitch_picture_lookup import KEEP_SECONDS, TwitchPictureLookup
from streamer_toolbox.core.widgets.kept_answers import KeptAnswers
from tests.fakes.fake_helix import FakeHelix

KIT = "https://static-cdn.jtvnw.net/jtv_user_pictures/kit-profile_image-300x300.png"
FOX = "https://static-cdn.jtvnw.net/jtv_user_pictures/fox-profile_image-300x300.png"


def users(params: dict) -> dict:
    known = [{"id": "11", "login": "kit", "profile_image_url": KIT}, {"id": "22", "login": "fox", "profile_image_url": FOX}]
    return {"data": [u for u in known if u["id"] in params.get("id", []) or u["login"] in params.get("login", [])]}


class TestTwitchPictureLookup(unittest.IsolatedAsyncioTestCase):
    """A profile picture's address: by id or name, many new people in one request, kept a day, never an error."""

    async def asyncSetUp(self) -> None:
        self.now = 1000.0
        self.helix = FakeHelix({("GET", "users"): users})
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "twitch_pictures.json"
        self.kept = KeptAnswers(self.path, 5000, KEEP_SECONDS, clock=lambda: self.now)
        self.lookup = TwitchPictureLookup(self.helix, wait=0.01, kept=self.kept)

    async def asyncTearDown(self) -> None:
        self.temp.cleanup()

    async def test_many_new_people_are_one_request(self) -> None:
        found = await asyncio.gather(self.lookup.picture("11"), self.lookup.picture("@Fox"),
                                     self.lookup.picture("11"), self.lookup.picture("nobody"))
        self.assertEqual([KIT.replace("300x300", "70x70"), FOX.replace("300x300", "70x70"),
                          KIT.replace("300x300", "70x70"), ""], found)
        self.assertEqual([({"id": ["11"], "login": ["fox", "nobody"]}, {})], self.helix.sent("GET", "users"))

    async def test_kept_for_a_day_also_after_a_restart(self) -> None:
        await self.lookup.picture("kit", "300x300")
        again = TwitchPictureLookup(self.helix, wait=0.01, kept=KeptAnswers(self.path, 5000, KEEP_SECONDS,
                                                                             clock=lambda: self.now))
        self.assertEqual(KIT, await again.picture("11", "300x300"))  # asked by name, known by id too
        self.assertEqual(1, len(self.helix.sent("GET", "users")))
        self.now += KEEP_SECONDS
        await again.picture("11")
        self.assertEqual(2, len(self.helix.sent("GET", "users")))  # a day later: asked again

    async def test_twitch_down_gives_the_old_address_or_nothing(self) -> None:
        await self.lookup.picture("11", "150x150")
        self.now += KEEP_SECONDS
        self.helix.answers[("GET", "users")] = TwitchApiError(500, "down")
        self.assertEqual(KIT.replace("300x300", "150x150"), await self.lookup.picture("11", "150x150"))
        self.assertEqual("", await self.lookup.picture("22"))
        self.assertEqual("", await self.lookup.picture("../x"))  # not a name: Twitch isn't asked
        self.assertEqual(3, len(self.helix.sent("GET", "users")))


if __name__ == "__main__":
    unittest.main()
