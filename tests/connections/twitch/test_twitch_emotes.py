import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.connections.twitch.boxes.twitch_emotes import TwitchEmotes
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.flows.current_box import current_box
from streamer_toolbox.core.media.media_buffer import MediaBuffer
from tests.fakes.fake_media_web import FakeMediaWeb

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


class TestTwitchEmotesFolder(unittest.IsolatedAsyncioTestCase):
    """His 11-16: "we should give them a folder name, and value name for it. Just in case someone wants to use it
    without our flow": Folder, twitch_emotes by default, shared by every box that names it."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.web = FakeMediaWeb()
        self.web.picture(KAPPA)
        self.buffer = MediaBuffer(Path(self._dir.name) / "media", self.web.transport, resolve=self.web.resolve)
        self.actions = ActionRegistry()
        self.actions.add_box(TwitchEmotes(self.buffer), "twitch")

    def tearDown(self) -> None:
        self._dir.cleanup()

    async def _in(self, flow: str, box: str, **fields) -> str:
        token = current_box.set((flow, box))
        try:
            found = await self.actions.run("twitch.emotes", emotes=[{"name": "Kappa", "id": "25"}], **fields)
        finally:
            current_box.reset(token)
        return found["emoji_dict"]["Kappa"]

    async def test_two_flows_share_the_default_folder(self) -> None:
        mine = await self._in("twitch_pfp_and_chat_emotes", "n6")
        theirs = await self._in("my_own_chat", "n3")
        self.assertEqual(1, len(self.web.asked))  # downloaded once for both
        self.assertTrue(mine.startswith("/toolbox/media/flows/box/twitch_pfp_and_chat_emotes/n6/"))
        self.assertTrue(theirs.startswith("/toolbox/media/flows/box/my_own_chat/n3/"))
        self.assertIsNotNone(self.buffer.find_shared("twitch_emotes", mine.rsplit("/", 1)[1]))

    async def test_empty_is_the_boxs_own_folder_and_a_wrong_name_stops_it(self) -> None:
        own = await self._in("flow_a", "n1", folder="")
        self.assertIsNone(self.buffer.find_shared("twitch_emotes", own.rsplit("/", 1)[1]))
        self.assertIsNotNone(self.buffer.find_for_box("flow_a", "n1", own.rsplit("/", 1)[1]))
        with self.assertRaisesRegex(ValueError, "folder name"):
            await self._in("flow_a", "n1", folder="my emotes!")


if __name__ == "__main__":
    unittest.main()
