import unittest

from streamer_toolbox.connections.twitch.boxes.twitch_emotes import TwitchEmotes
from streamer_toolbox.core.actions.action_registry import ActionRegistry

KAPPA = "https://static-cdn.jtvnw.net/emoticons/v2/25/default/dark/3.0"


class TestTwitchEmotes(unittest.IsolatedAsyncioTestCase):
    """His 2026-11-16: the message's Twitch emotes as an emoji dictionary, {"Kappa": its picture's address}."""

    def setUp(self) -> None:
        self.actions = ActionRegistry()
        self.actions.add_box(TwitchEmotes(), "twitch")

    async def test_the_messages_emotes_become_name_and_picture(self) -> None:
        emotes = [{"name": "Kappa", "id": "25", "start": 0, "end": 4},
                  {"name": "Kappa", "id": "25", "start": 10, "end": 14},  # twice in the message: once in it
                  {"name": "kitWave", "id": "emotesv2_abc", "start": 16, "end": 22}]
        self.assertEqual({"emoji_dict": {"Kappa": KAPPA, "kitWave": KAPPA.replace("25", "emotesv2_abc")}},
                         await self.actions.run("twitch.emotes", emotes=emotes))

    async def test_light_pictures_and_emotes_written_as_json(self) -> None:
        found = await self.actions.run("twitch.emotes", emotes='[{"name": "Kappa", "id": "25"}]', theme="light")
        self.assertEqual({"Kappa": KAPPA.replace("dark", "light")}, found["emoji_dict"])

    async def test_no_emotes_an_empty_dictionary(self) -> None:
        for nothing in (None, "", [], [{"name": "", "id": "1"}, {"name": "x"}, "Kappa"]):
            self.assertEqual({"emoji_dict": {}}, await self.actions.run("twitch.emotes", emotes=nothing))

    async def test_what_isnt_a_list_or_a_theme_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "aren't a list"):
            await self.actions.run("twitch.emotes", emotes="Kappa")
        with self.assertRaisesRegex(ValueError, "dark or light"):
            await self.actions.run("twitch.emotes", emotes=[], theme="pink")


if __name__ == "__main__":
    unittest.main()
