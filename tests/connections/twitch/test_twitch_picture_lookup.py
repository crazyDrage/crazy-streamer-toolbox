import asyncio
import unittest

from streamer_toolbox.connections.twitch.twitch_api_error import TwitchApiError
from streamer_toolbox.connections.twitch.twitch_picture_lookup import TwitchPictureLookup
from tests.fakes.fake_helix import FakeHelix

KIT = "https://static-cdn.jtvnw.net/jtv_user_pictures/kit-profile_image-300x300.png"
FOX = "https://static-cdn.jtvnw.net/jtv_user_pictures/fox-profile_image-300x300.png"


def users(params: dict) -> dict:
    known = [{"id": "11", "login": "kit", "profile_image_url": KIT}, {"id": "22", "login": "fox", "profile_image_url": FOX}]
    return {"data": [u for u in known if u["id"] in params.get("id", []) or u["login"] in params.get("login", [])]}


class TestTwitchPictureLookup(unittest.IsolatedAsyncioTestCase):
    """A profile picture's address: by id or name, many people in one request, nothing kept, never an error."""

    async def asyncSetUp(self) -> None:
        self.helix = FakeHelix({("GET", "users"): users})
        self.lookup = TwitchPictureLookup(self.helix, wait=0.01)

    async def test_many_people_are_one_request(self) -> None:
        found = await asyncio.gather(self.lookup.picture("11"), self.lookup.picture("@Fox"),
                                     self.lookup.picture("11"), self.lookup.picture("nobody"))
        self.assertEqual([KIT.replace("300x300", "70x70"), FOX.replace("300x300", "70x70"),
                          KIT.replace("300x300", "70x70"), ""], found)
        self.assertEqual([({"id": ["11"], "login": ["fox", "nobody"]}, {})], self.helix.sent("GET", "users"))

    async def test_nothing_is_kept_here_a_second_time_asks_again(self) -> None:
        await self.lookup.picture("11", "300x300")  # his round 90: Remembered value keeps it, in the flow
        self.assertEqual(KIT, await self.lookup.picture("11", "300x300"))
        self.assertEqual(2, len(self.helix.sent("GET", "users")))

    async def test_twitch_down_gives_nothing(self) -> None:
        self.helix.answers[("GET", "users")] = TwitchApiError(500, "down")
        self.assertEqual("", await self.lookup.picture("22"))
        self.assertEqual("", await self.lookup.picture("../x"))  # not a name: Twitch isn't asked
        self.assertEqual(1, len(self.helix.sent("GET", "users")))


if __name__ == "__main__":
    unittest.main()
