import tempfile
import unittest
from pathlib import Path

import httpx

from streamer_toolbox.connections.twitch.twitch_clip_question import TwitchClipQuestion
from tests.fakes.player_code import QUESTION, player_code

ASSETS = "https://assets.twitch.tv/assets"
PAGE = (f'<html><script src="{ASSETS}/vendor-1.js"></script><script src="{ASSETS}/player-2.js"></script>'
        f'<script src="https://evil.test/assets/x.js"></script><script src="{ASSETS}/late-3.js"></script></html>')


class TestTwitchClipQuestion(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.keep = Path(self._dir.name) / "cache" / "question.json"
        self.now = 1000.0
        self.asked: list[str] = []
        self.files = {f"{ASSETS}/vendor-1.js": "var a=1;", f"{ASSETS}/player-2.js": player_code(),
                      f"{ASSETS}/late-3.js": "var z=1;"}

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _answer(self, request: httpx.Request) -> httpx.Response:
        self.asked.append(str(request.url))
        if request.url.host == "clips.twitch.tv":
            return httpx.Response(200, text=PAGE)
        text = self.files.get(str(request.url))
        return httpx.Response(404) if text is None else httpx.Response(200, text=text)

    def finder(self) -> TwitchClipQuestion:
        return TwitchClipQuestion(self.keep, httpx.MockTransport(self._answer), now=lambda: self.now)

    async def test_it_reads_the_players_code_files_until_one_holds_the_question(self) -> None:
        found = await self.finder().find()
        self.assertEqual((found["question"], found["variables"], found["fresh"]),
                         (QUESTION, ["slug", "platform", "codecs"], True))
        self.assertEqual([address.rsplit("/", 1)[-1] for address in self.asked[1:]], ["vendor-1.js", "player-2.js"])
        self.assertFalse(any("evil.test" in address for address in self.asked))  # only Twitch's own code addresses

    async def test_what_was_found_is_kept_for_a_week(self) -> None:
        await self.finder().find()
        self.asked.clear()
        self.now += 6 * 24 * 3600
        again = await self.finder().find()  # a new start of the toolbox: read from the file
        self.assertEqual((again["question"], again["fresh"], self.asked), (QUESTION, False, []))
        self.now += 2 * 24 * 3600
        self.assertTrue((await self.finder().find())["fresh"])
        self.asked.clear()
        self.assertTrue((await self.finder().find(again=True))["fresh"])  # asked to read anew
        self.assertEqual(len(self.asked), 3)

    async def test_a_player_without_the_question_is_said_plainly(self) -> None:
        self.files[f"{ASSETS}/player-2.js"] = player_code("Renamed_Question")
        with self.assertRaisesRegex(RuntimeError, "doesn't hold the question VideoAccessToken_Clip any more "
                                                  r"\(3 code files read\)"):
            await self.finder().find()
        self.assertFalse(self.keep.exists())

    async def test_a_code_file_that_is_missing_or_huge_is_skipped(self) -> None:
        del self.files[f"{ASSETS}/vendor-1.js"]
        self.files[f"{ASSETS}/late-3.js"] = self.files.pop(f"{ASSETS}/player-2.js")
        self.files[f"{ASSETS}/player-2.js"] = "x" * 7_000_000
        self.assertEqual((await self.finder().find())["from"], f"{ASSETS}/late-3.js")

    async def test_without_internet_it_says_so(self) -> None:
        def offline(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("no internet")

        with self.assertRaisesRegex(RuntimeError, "player could not be read"):
            await TwitchClipQuestion(None, httpx.MockTransport(offline)).find()


if __name__ == "__main__":
    unittest.main()
