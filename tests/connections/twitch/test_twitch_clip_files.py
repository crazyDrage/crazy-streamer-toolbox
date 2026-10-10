import json
import unittest

import httpx

from streamer_toolbox.connections.twitch.twitch_clip_files import TwitchClipFiles, clip_id

TOKEN = json.dumps({"authorization": {"forbidden": False, "reason": ""}, "clip_slug": "Abc-1", "expires": 1})
CLIP = {"playbackAccessToken": {"signature": "s1g", "value": TOKEN},
        "videoQualities": [{"quality": "480", "frameRate": 30, "sourceURL": "https://cdn.test/a/480/index.mp4"},
                           {"quality": "1080", "frameRate": 60, "sourceURL": "https://cdn.test/a/1080/index.mp4"}]}


class TestTwitchClipFiles(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.answer: httpx.Response | Exception = httpx.Response(200, json={"data": {"clip": CLIP}})
        self.asked: list[httpx.Request] = []
        self.files = TwitchClipFiles(httpx.MockTransport(self._answer))

    def _answer(self, request: httpx.Request) -> httpx.Response:
        self.asked.append(request)
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer

    async def test_the_files_best_first_each_with_the_signature(self) -> None:
        files = await self.files.files("https://clips.twitch.tv/Abc-1?tt_medium=x")
        self.assertEqual([one["quality"] for one in files], [1080, 480])
        address = httpx.URL(files[0]["address"])
        self.assertEqual((address.host, address.path), ("cdn.test", "/a/1080/index.mp4"))
        self.assertEqual((address.params["sig"], address.params["token"]), ("s1g", TOKEN))
        sent = json.loads(self.asked[0].content)
        self.assertEqual((sent["operationName"], sent["variables"]["slug"]), ("VideoAccessToken_Clip", "Abc-1"))
        self.assertTrue(self.asked[0].headers["Client-ID"])
        self.assertNotIn("Authorization", self.asked[0].headers)  # no login is sent

    async def test_a_clip_twitch_does_not_know_or_refuses_is_said_plainly(self) -> None:
        self.answer = httpx.Response(200, json={"data": {"clip": None}})
        with self.assertRaisesRegex(RuntimeError, "doesn't know the clip Gone"):
            await self.files.files("Gone")
        refused = json.dumps({"authorization": {"forbidden": True, "reason": "GEOBLOCKED"}})
        self.answer = httpx.Response(200, json={"data": {"clip": {**CLIP, "playbackAccessToken": {
            "signature": "s", "value": refused}}}})
        with self.assertRaisesRegex(RuntimeError, "doesn't let this clip be played: GEOBLOCKED"):
            await self.files.files("Abc-1")
        with self.assertRaisesRegex(ValueError, "which clip"):
            await self.files.files("  ")

    async def test_when_twitch_forgot_the_stored_question_it_is_asked_written_out(self) -> None:
        def answer(request: httpx.Request) -> httpx.Response:
            self.asked.append(request)
            if "extensions" in json.loads(request.content):
                return httpx.Response(200, json={"errors": [{"message": "PersistedQueryNotFound"}]})
            return httpx.Response(200, json={"data": {"clip": CLIP}})

        files = await TwitchClipFiles(httpx.MockTransport(answer)).files("Abc-1")
        self.assertEqual([one["quality"] for one in files], [1080, 480])
        second = json.loads(self.asked[1].content)
        self.assertEqual((len(self.asked), second["variables"]), (2, {"slug": "Abc-1"}))
        self.assertIn("playbackAccessToken", second["query"])
        self.assertNotIn("extensions", second)

    async def test_when_twitch_refuses_both_known_ways_the_finder_asks_as_the_player_does(self) -> None:
        found = {"question": "query New($slug: ID!, $platform: String!, $codecs: [C!]) { clip { id } }",
                 "variables": ["slug", "platform", "codecs"], "fresh": False}
        finds: list[bool] = []

        class Finder:
            async def find(self, again: bool = False) -> dict:
                finds.append(again)
                return {**found, "fresh": again}

        def answer(request: httpx.Request) -> httpx.Response:
            sent = json.loads(request.content)
            self.asked.append(request)
            if sent.get("query") == found["question"] and len(finds) == 2:  # only the one read anew is taken
                return httpx.Response(200, json={"data": {"clip": CLIP}})
            return httpx.Response(200, json={"errors": [{"message": "PersistedQueryNotFound"}]})

        files = TwitchClipFiles(httpx.MockTransport(answer), question=Finder())
        with self.assertRaisesRegex(RuntimeError, "way to ask may have changed"):
            await files.files("Abc-1", finder=False)  # switched off in the box: the finder is not used
        self.assertEqual((finds, len(self.asked)), ([], 2))
        self.assertEqual([one["quality"] for one in await files.files("Abc-1")], [1080, 480])
        self.assertEqual(finds, [False, True])  # the kept question was refused, so the player was read anew
        self.assertEqual(json.loads(self.asked[-1].content)["variables"], {"slug": "Abc-1", "platform": "web"})

    async def test_a_finder_that_finds_nothing_leaves_the_plain_reason(self) -> None:
        class Finder:
            async def find(self, again: bool = False) -> dict:
                raise RuntimeError("Twitch's player doesn't hold the question any more")

        self.answer = httpx.Response(200, json={"errors": [{"message": "PersistedQueryNotFound"}]})
        with self.assertLogs("streamer_toolbox.connections.twitch.twitch_clip_files", "WARNING"):
            with self.assertRaisesRegex(RuntimeError, "way to ask may have changed"):
                await TwitchClipFiles(httpx.MockTransport(self._answer), question=Finder()).files("Abc-1")

    async def test_a_changed_or_unreachable_twitch_is_said_plainly(self) -> None:
        for answer in (httpx.Response(200, json={"errors": [{"message": "PersistedQueryNotFound"}]}),
                       httpx.Response(400, text="no"), httpx.Response(200, text="<html>"),
                       httpx.ConnectError("no route")):
            self.answer = answer
            with self.assertRaisesRegex(RuntimeError, "way to ask (may have|has) changed"):
                await self.files.files("Abc-1")
        self.answer = httpx.Response(200, json={"data": {"clip": {**CLIP, "videoQualities": []}}})
        with self.assertRaisesRegex(RuntimeError, "no video file"):
            await self.files.files("Abc-1")

    def test_a_clips_id_from_its_links(self) -> None:
        for text in ("Abc-1", " Abc-1 ", "https://clips.twitch.tv/Abc-1", "clips.twitch.tv/Abc-1/",
                     "https://www.twitch.tv/kit/clip/Abc-1?filter=clips&range=7d"):
            self.assertEqual(clip_id(text), "Abc-1", text)


if __name__ == "__main__":
    unittest.main()
