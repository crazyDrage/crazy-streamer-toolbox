import unittest

from streamer_toolbox.connections.twitch.boxes.twitch_profile_picture import TwitchProfilePicture
from streamer_toolbox.connections.twitch.twitch_picture_lookup import TwitchPictureLookup
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from tests.fakes.fake_helix import FakeHelix

KIT = "https://static-cdn.jtvnw.net/jtv_user_pictures/kit-profile_image-300x300.png"


class TestTwitchProfilePicture(unittest.IsolatedAsyncioTestCase):
    """The box: someone's picture address for an event's `picture` value."""

    async def asyncSetUp(self) -> None:
        self.helix = FakeHelix({("GET", "users"): {"data": [{"id": "11", "login": "kit", "profile_image_url": KIT}]}})
        self.actions = ActionRegistry()
        self.actions.add_box(TwitchProfilePicture(TwitchPictureLookup(self.helix, wait=0)), "twitch")

    async def test_gives_the_address_in_the_size_asked(self) -> None:
        self.assertEqual({"picture": KIT.replace("300x300", "70x70")},
                         await self.actions.run("twitch.profile_picture", user_id="11"))
        self.assertEqual({"picture": KIT},
                         await self.actions.run("twitch.profile_picture", user_id="11", size="300x300"))

    async def test_only_twitch_its_field_is_the_user_id_and_there_is_no_platform_field(self) -> None:
        action = self.actions.get("twitch.profile_picture")  # his round 90: no hidden platform filter
        self.assertEqual("Twitch user id", action.labels["user_id"])
        with self.assertRaises(TypeError):
            await self.actions.run("twitch.profile_picture", user_id="11", platform="youtube")

    async def test_an_empty_user_id_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "whose picture"):
            await self.actions.run("twitch.profile_picture", user_id=" ")


if __name__ == "__main__":
    unittest.main()
