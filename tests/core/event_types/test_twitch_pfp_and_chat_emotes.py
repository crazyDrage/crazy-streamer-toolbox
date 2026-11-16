import tempfile
import unittest
from pathlib import Path

import httpx

from streamer_toolbox.connections.twitch.boxes.bttv_emotes import BttvEmotes
from streamer_toolbox.connections.twitch.boxes.twitch_emotes import EMOTE_PICTURE, TwitchEmotes
from streamer_toolbox.connections.twitch.boxes.twitch_profile_picture import TwitchProfilePicture
from streamer_toolbox.connections.twitch.twitch_picture_lookup import TwitchPictureLookup
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.cache.remembered_actions import RememberedActions
from streamer_toolbox.core.cache.remembered_values import RememberedValues
from streamer_toolbox.core.data.object_actions import ObjectActions
from streamer_toolbox.core.event_types.event_flows import twitch_pfp_and_chat_emotes
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.logic_actions import LogicActions
from streamer_toolbox.core.media.media_actions import MediaActions
from streamer_toolbox.core.media.media_buffer import MediaBuffer
from streamer_toolbox.core.variables.variable_store import VariableStore
from streamer_toolbox.core.widgets.emote_lookup import EmoteLookup
from streamer_toolbox.core.widgets.kept_answers import KeptAnswers
from tests.fakes.fake_helix import FakeHelix
from tests.fakes.fake_media_web import FakeMediaWeb

KIT = "https://static-cdn.jtvnw.net/jtv_user_pictures/kit-profile_image-70x70.png"
KAPPA = EMOTE_PICTURE.format(id="25", theme="dark")
LURK = "https://cdn.betterttv.net/emote/b1/3x"
# BetterTTV: the global ones and channel 42's (its own Kappa too: Twitch's wins)
BTTV = {"/3/cached/emotes/global": [{"id": "g1", "code": "Kappa"}],
        "/3/cached/users/twitch/42": {"channelEmotes": [{"id": "b1", "code": "crazyLurk"}], "sharedEmotes": []}}


class TestTwitchPfpAndChatEmotes(unittest.IsolatedAsyncioTestCase):
    """His 11-16: "twitch pfp and chat emotes", a flow used as a box. "Make sure if one of them is None, it will
    not fail": a missing user id or missing emotes are left out."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        folder = Path(self._dir.name)
        self.helix = FakeHelix({("GET", "users"): {"data": [{"id": "11", "login": "kit", "profile_image_url": KIT}]}})
        self.web = FakeMediaWeb()
        self.web.picture(KIT)
        self.web.picture(KAPPA)
        buffer = MediaBuffer(folder / "media", self.web.transport, resolve=self.web.resolve)
        actions = ActionRegistry()
        variables = VariableStore(folder / "variables")
        LogicActions(variables).add_to(actions)
        RememberedActions(RememberedValues(folder / "remembered.json")).add_to(actions)
        MediaActions(buffer).add_to(actions)
        actions.add_box(TwitchProfilePicture(TwitchPictureLookup(self.helix, wait=0)), "twitch")
        actions.add_box(TwitchEmotes(buffer), "twitch")
        self.bttv_asked: list[str] = []
        lookup = EmoteLookup(httpx.MockTransport(self._bttv))
        actions.add_box(BttvEmotes(lookup, KeptAnswers(), lambda: "42", buffer), "twitch")
        ObjectActions().add_to(actions)
        self.web.picture(LURK)
        self.runner = FlowRunner(actions, variables)
        self.flow = twitch_pfp_and_chat_emotes("twitch_pfp_and_chat_emotes")

    def _bttv(self, request: httpx.Request) -> httpx.Response:
        self.bttv_asked.append(request.url.path)
        return httpx.Response(200, json=BTTV[request.url.path]) if request.url.path in BTTV else httpx.Response(404)

    def tearDown(self) -> None:
        self._dir.cleanup()

    async def _out(self, **inputs) -> dict:
        results = await self.runner.run(self.flow, inputs=inputs)
        return next(r["result"] for r in results if r["box"] == "n7")  # the End box

    async def test_both(self) -> None:
        out = await self._out(user_id="11", user_login="kit", emotes=[{"name": "Kappa", "id": "25"}],
                              message="hi Kappa crazyLurk")
        self.assertRegex(out["picture"], r"^/toolbox/media/flows/box/twitch_pfp_and_chat_emotes/n4/")
        self.assertEqual({"Kappa", "crazyLurk"}, set(out["emoji_dict"]))
        # his 11-16: a dictionary of each, joined; Kappa is Twitch's own (n6), crazyLurk BetterTTV's (n8)
        self.assertRegex(out["emoji_dict"]["Kappa"], r"^/toolbox/media/flows/box/twitch_pfp_and_chat_emotes/n6/")
        self.assertRegex(out["emoji_dict"]["crazyLurk"],
                         r"^/toolbox/media/flows/box/twitch_pfp_and_chat_emotes/n8/")

    async def test_nothing_given_nothing_fails(self) -> None:
        self.assertEqual({"picture": "", "emoji_dict": {}}, await self._out())
        self.assertEqual([], self.helix.calls)  # no user id: Twitch isn't asked
        self.assertEqual([], self.bttv_asked)  # no message: BetterTTV isn't asked

    async def test_only_emotes(self) -> None:
        out = await self._out(user_id="", emotes=[{"name": "Kappa", "id": "25"}])
        self.assertEqual("", out["picture"])
        self.assertEqual(["Kappa"], list(out["emoji_dict"]))

    async def test_only_the_user(self) -> None:
        out = await self._out(user_id="11", user_login="kit")
        self.assertTrue(out["picture"])
        self.assertEqual({}, out["emoji_dict"])

    async def test_an_emote_is_downloaded_once(self) -> None:
        """His "we save bandwidth even with a few emotes"."""
        first = await self._out(emotes=[{"name": "Kappa", "id": "25"}])
        again = await self._out(emotes=[{"name": "Kappa", "id": "25"}])
        self.assertEqual(first, again)
        self.assertEqual(1, len(self.web.asked))


if __name__ == "__main__":
    unittest.main()
