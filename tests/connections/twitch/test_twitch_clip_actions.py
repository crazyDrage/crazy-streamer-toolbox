import unittest

from streamer_toolbox.connections.twitch.twitch_clip_actions import TwitchClipActions
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from tests.fakes.fake_clip_files import FakeClipFiles


class TestTwitchClipActions(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.files = FakeClipFiles()
        self.actions = ActionRegistry()
        TwitchClipActions(self.files).add_to(self.actions)

    async def address(self, **params) -> dict:
        return await self.actions.run("twitch.clip_address", **params)

    async def test_the_best_file_unless_a_quality_is_asked_for(self) -> None:
        self.assertEqual(await self.address(clip="https://clips.twitch.tv/Abc-1"), {
            "address": "https://cdn.test/https://clips.twitch.tv/Abc-1/1080.mp4", "quality": 1080, "id": "Abc-1",
            "found": True, "problem": ""})
        self.assertEqual((await self.address(clip="Abc-1", quality="720"))["quality"], 720)
        self.assertEqual((await self.address(clip="Abc-1", quality="480p"))["quality"], 360)  # the best below it
        self.assertEqual((await self.address(clip="Abc-1", quality="Best"))["quality"], 1080)

    async def test_a_clip_that_only_has_better_ones_gives_its_smallest(self) -> None:
        self.files.qualities = (1080, 720)
        self.assertEqual((await self.address(clip="Abc-1", quality="360"))["quality"], 720)
        with self.assertRaisesRegex(ValueError, "quality is best, 1080"):
            await self.address(clip="Abc-1", quality="sharp")

    async def test_the_question_finder_is_on_unless_the_box_switches_it_off(self) -> None:
        await self.address(clip="Abc-1")
        await self.address(clip="Abc-1", finder="false")
        await self.address(clip="Abc-1", finder=True)
        self.assertEqual(self.files.finder, [True, False, True])

    async def test_with_fail_off_no_address_is_found_false_so_an_if_can_take_another_way(self) -> None:
        self.files.refused = "Twitch doesn't let this clip be played: age restricted"
        with self.assertRaisesRegex(RuntimeError, "age restricted"):
            await self.address(clip="Abc-1")
        self.assertEqual(await self.address(clip="Abc-1", fail_on_error="false"), {
            "address": "", "quality": 0, "id": "Abc-1", "found": False,
            "problem": "Twitch doesn't let this clip be played: age restricted"})

    async def test_the_box_offers_its_qualities(self) -> None:
        box = self.actions.get("twitch.clip_address")
        self.assertEqual(await box.options["quality"](), ["best", "1080", "720", "480", "360"])
        self.assertEqual(set(box.outputs), {"address", "quality", "id", "found", "problem"})


if __name__ == "__main__":
    unittest.main()
