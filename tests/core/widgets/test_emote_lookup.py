import unittest

import httpx

from streamer_toolbox.core.widgets.emote_lookup import EmoteLookup
from streamer_toolbox.core.widgets.kept_answers import KeptAnswers

ANSWERS = {
    "/3/cached/emotes/global": [{"id": "g1", "code": ":tf:", "animated": False},
                                {"id": "g2", "code": ":'(", "animated": False}],
    "/3/cached/users/twitch/42": {"channelEmotes": [{"id": "b1", "code": "crazyLurk", "animated": True}],
                                  "sharedEmotes": [{"id": "b2", "code": "Clap", "width": 32, "height": 32}]},
    "/v1/set/global": {"default_sets": [3], "sets": {
        "3": {"emoticons": [{"id": 9, "name": "ZreknarF", "width": 40, "height": 30,
                             "urls": {"1": "https://cdn.frankerfacez.com/emote/9/1", "2": None, "4": None}}]},
        "77": {"emoticons": [{"id": 5, "name": "OnlyForSome", "urls": {"1": "https://x/5/1"}}]}}},
    "/v1/room/id/42": {"room": {"set": 8}, "sets": {"8": {"emoticons": [
        {"id": 7, "name": "dragonHi", "width": 28, "height": 28, "animated": {"1": "x"},
         "urls": {"1": "https://cdn.frankerfacez.com/emote/7/1", "2": "https://cdn.frankerfacez.com/emote/7/2",
                  "4": "https://cdn.frankerfacez.com/emote/7/4"}}]}}},
}


class TestEmoteLookup(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.asked: list[str] = []
        self.down: set[str] = set()
        self.now = 0.0
        self.kept = KeptAnswers(keep_seconds=60, clock=lambda: self.now)
        self.lookup = EmoteLookup(httpx.MockTransport(self._answer))

    def _answer(self, request: httpx.Request) -> httpx.Response:
        self.asked.append(f"{request.url.host}{request.url.path}")
        if request.url.host in self.down:
            raise httpx.ConnectError("not reachable")
        if request.url.path in ANSWERS:
            return httpx.Response(200, json=ANSWERS[request.url.path])
        return httpx.Response(404, json={"message": "not known here"})

    async def test_a_channels_emotes_in_streamelements_shape(self) -> None:
        emotes = await self.lookup.emotes("42", self.kept)
        self.assertEqual(emotes["bttvChannelEmotes"], {
            "crazyLurk": {"name": "crazyLurk", "_id": "b1", "type": "bttv", "width": 28, "height": 28, "gif": True,
                          "urls": {"1": "https://cdn.betterttv.net/emote/b1/1x",
                                   "2": "https://cdn.betterttv.net/emote/b1/2x",
                                   "4": "https://cdn.betterttv.net/emote/b1/3x"}},
            "Clap": {"name": "Clap", "_id": "b2", "type": "bttv", "width": 32, "height": 32, "gif": False,
                     "urls": {"1": "https://cdn.betterttv.net/emote/b2/1x",
                              "2": "https://cdn.betterttv.net/emote/b2/2x",
                              "4": "https://cdn.betterttv.net/emote/b2/3x"}}})
        self.assertEqual(emotes["ffzChannelEmotes"]["dragonHi"]["urls"]["4"],
                         "https://cdn.frankerfacez.com/emote/7/4")
        self.assertEqual(emotes["ffzChannelEmotes"]["dragonHi"]["gif"], True)
        # the global ones: only FrankerFaceZ's default sets; a missing size falls back to a smaller one
        self.assertEqual(list(emotes["ffzGlobalEmotes"]), ["ZreknarF"])
        self.assertEqual(emotes["ffzGlobalEmotes"]["ZreknarF"]["urls"]["4"], "https://cdn.frankerfacez.com/emote/9/1")
        # a name that can't be a regular expression would stop a chat widget at every message
        self.assertEqual(list(emotes["bttvGlobalEmotes"]), [":tf:"])

    async def test_a_channel_that_isnt_known_there_has_none_and_answers_are_kept(self) -> None:
        emotes = await self.lookup.emotes("999", self.kept)
        self.assertEqual((emotes["bttvChannelEmotes"], emotes["ffzChannelEmotes"]), ({}, {}))
        self.assertEqual(list(emotes["bttvGlobalEmotes"]), [":tf:"])
        await self.lookup.emotes("999", self.kept)
        await self.lookup.emotes("42", self.kept)
        self.assertEqual(len(self.asked), 6)  # global twice, 999 twice, 42 twice: each asked once
        self.assertEqual((await self.lookup.emotes("not-a-twitch-id", self.kept))["bttvChannelEmotes"], {})
        self.assertEqual(len(self.asked), 6)
        self.now = 61
        await self.lookup.emotes("42", self.kept)
        self.assertEqual(len(self.asked), 10)

    async def test_a_service_that_cant_be_reached_gives_empty_lists_and_isnt_kept(self) -> None:
        self.down = {"api.frankerfacez.com"}
        emotes = await self.lookup.emotes("42", self.kept)
        self.assertEqual((list(emotes["bttvChannelEmotes"]), emotes["ffzChannelEmotes"], emotes["ffzGlobalEmotes"]),
                         (["crazyLurk", "Clap"], {}, {}))
        self.down = set()
        self.assertEqual(list((await self.lookup.emotes("42", self.kept))["ffzChannelEmotes"]), ["dragonHi"])


if __name__ == "__main__":
    unittest.main()
