import unittest

import httpx

from streamer_toolbox.connections.twitch.boxes.bttv_emotes import BttvEmotes
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.widgets.emote_lookup import EmoteLookup
from streamer_toolbox.core.widgets.kept_answers import KeptAnswers

ANSWERS = {"/3/cached/emotes/global": [{"id": "g1", "code": "catJAM"}, {"id": "g2", "code": "Clap"}],
           "/3/cached/users/twitch/42": {"channelEmotes": [{"id": "b1", "code": "crazyLurk"}],
                                         "sharedEmotes": [{"id": "b2", "code": "Clap"}]}}


def picture(emote_id: str) -> str:
    return f"https://cdn.betterttv.net/emote/{emote_id}/3x"


class TestBttvEmotes(unittest.IsolatedAsyncioTestCase):
    """His 11-16: "add the betterTTV one now", a dictionary of its own ("then add the 2 dicts together")."""

    def setUp(self) -> None:
        self.asked: list[str] = []
        self.down = False
        self.actions = ActionRegistry()
        self.actions.add_box(BttvEmotes(EmoteLookup(httpx.MockTransport(self._answer)), KeptAnswers(),
                                        lambda: "42"), "twitch")

    def _answer(self, request: httpx.Request) -> httpx.Response:
        self.asked.append(request.url.path)
        if self.down:
            raise httpx.ConnectError("not reachable")
        if request.url.path in ANSWERS:
            return httpx.Response(200, json=ANSWERS[request.url.path])
        return httpx.Response(404)

    async def _run(self, **fields) -> dict:
        return (await self.actions.run("twitch.bttv_emotes", **fields))["emoji_dict"]

    async def test_the_words_of_the_message_that_are_bttv_emotes(self) -> None:
        self.assertEqual({"catJAM": picture("g1"), "crazyLurk": picture("b1"), "Clap": picture("b2")},
                         await self._run(message="catJAM crazyLurk Clap catjam Kappa"))  # the channel's Clap wins

    async def test_bttv_is_asked_once_in_a_while_not_per_message(self) -> None:
        await self._run(message="catJAM")
        await self._run(message="crazyLurk")
        self.assertEqual(["/3/cached/emotes/global", "/3/cached/users/twitch/42"], self.asked)

    async def test_another_channel(self) -> None:
        self.assertEqual({"catJAM": picture("g1")}, await self._run(message="catJAM crazyLurk", channel="7"))

    async def test_no_message_no_question_and_bttv_down_no_failure(self) -> None:
        self.assertEqual({}, await self._run(message=""))
        self.assertEqual([], self.asked)
        self.down = True
        self.assertEqual({}, await self._run(message="catJAM"))
        self.down = False
        self.assertEqual({"catJAM": picture("g1")}, await self._run(message="catJAM"))  # not kept while down


if __name__ == "__main__":
    unittest.main()
