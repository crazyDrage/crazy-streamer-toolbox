import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.connections.obs.obs_media_playback import ObsMediaPlayback
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.connections.twitch.twitch_clip_actions import TwitchClipActions
from streamer_toolbox.connections.twitch.twitch_stream_actions import TwitchStreamActions
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_input import FlowInput
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_wire import START, FlowWire
from streamer_toolbox.core.flows.logic_actions import LogicActions
from streamer_toolbox.core.variables.variable_store import VariableStore
from tests.fakes.fake_clip_files import FakeClipFiles
from tests.fakes.fake_helix import FakeHelix
from tests.fakes.fake_obs_script import FakeObsScript

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)
TRIES = ((60, True), (60, False), (365, True), (365, False))
ENDED = {"mediaState": "OBS_MEDIA_STATE_ENDED", "mediaDuration": 9000, "mediaCursor": 9000}


def shoutout_flow() -> Flow:
    """His shoutout flow (2026-10-09): four tries to find a clip, each saved into one variable and checked by
    an If; the first that finds one goes on to Clip video address and Play video once; none: a chat line."""
    nodes, wires, previous, port = [], [], START, "out"
    for number, (days, featured) in enumerate(TRIES, 1):
        params = {"user": "${input.name}", "max_seconds": 60, "days": days, **({"featured": True} if featured else {})}
        nodes += [FlowNode(f"get{number}", "twitch.get_clips", params, save_as="shoutout_clip"),
                  FlowNode(f"if{number}", "logic.if", {"left": f"${{box.get{number}.count}}", "op": ">", "right": 0})]
        wires += [FlowWire(previous, port, f"get{number}"), FlowWire(f"get{number}", "done", f"if{number}"),
                  FlowWire(f"if{number}", "then", "address")]
        previous, port = f"if{number}", "else"
    nodes += [FlowNode("none", "twitch.send_chat", {"message": "No clip found for ${input.name}"}),
              FlowNode("address", "twitch.clip_address", {"clip": "${var.shoutout_clip.id}", "quality": "720"}),
              FlowNode("play", "obs.play_video_once", {"scene": "toolbox_test", "file": "${box.address.address}"}),
              FlowNode("after", "twitch.send_chat", {"message": "that was: ${var.shoutout_clip.title}"})]
    wires += [FlowWire(previous, port, "none"), FlowWire("address", "done", "play"),
              FlowWire("play", "done", "after")]
    return Flow("shoutout_clip", "Shoutout clip", tuple(nodes), tuple(wires), inputs=(FlowInput("name", ""),))


class TestShoutoutClipFlow(unittest.IsolatedAsyncioTestCase):
    """The whole shoutout with a clip, on the real boxes with Twitch and OBS faked: which try finds the clip,
    and that the boxes after the Ifs play the one that was found."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.clips: dict[tuple[int, bool], list[dict]] = {}  # (days, only featured) → what Twitch has
        self.helix = FakeHelix({("GET", "users"): {"data": [{"id": "77", "login": "kit"}]},
                                ("GET", "clips"): self._clips})
        self.obs = FakeObsScript({"CreateInput": {"sceneItemId": 12, "inputUuid": "u"},
                                  "GetMediaInputStatus": [ENDED]})
        self.chat: list[str] = []
        actions = ActionRegistry()
        variables = VariableStore(Path(self._dir.name) / "variables.json")
        me = OAuthToken("a", "r", 0, (), "42", "streamer")
        TwitchStreamActions(self.helix, lambda: me, pick=lambda clips: clips[0], now=lambda: NOW).add_to(actions)
        TwitchClipActions(FakeClipFiles()).add_to(actions)
        ObsMediaPlayback(ObsRequests(self.obs.call), poll_seconds=0, start_timeout=0.5).add_to(actions)
        LogicActions(variables).add_to(actions)
        actions.add("twitch.send_chat", self._say, "")
        self.runner = FlowRunner(actions, variables)

    def tearDown(self) -> None:
        self._dir.cleanup()

    async def _say(self, message: str) -> None:
        self.chat.append(message)

    def _clips(self, params: dict) -> dict:
        days = 60 if params["started_at"].startswith("2026-08") else 365
        return {"data": self.clips.get((days, "is_featured" in params), [])}

    async def _shout(self) -> list[str]:
        """Runs the flow for kit; gives the files OBS was told to play."""
        await self.runner.run(shoutout_flow(), inputs={"name": "kit"})
        return [made["inputSettings"]["input"] for made in self.obs.sent("CreateInput")]

    async def test_a_featured_clip_of_the_last_60_days_is_found_at_the_first_try(self) -> None:
        self.clips[(60, True)] = [{"id": "New", "title": "fresh", "duration": 20}]
        self.assertEqual(await self._shout(), ["https://cdn.test/New/720.mp4"])
        self.assertEqual(len(self.helix.sent("GET", "clips")), 1)
        self.assertEqual(self.chat, ["that was: fresh"])  # after the clip was over
        self.assertEqual(self.obs.kinds()[-1], "RemoveInput")

    async def test_only_an_old_clip_that_is_not_featured_is_found_at_the_last_try(self) -> None:
        self.clips[(365, False)] = [{"id": "Old", "title": "classic", "duration": 30}]
        self.assertEqual(await self._shout(), ["https://cdn.test/Old/720.mp4"])
        asked = [("is_featured" in params, params["started_at"][:10]) for params, _ in self.helix.sent("GET", "clips")]
        self.assertEqual(asked, [(True, "2026-08-10"), (False, "2026-08-10"), (True, "2025-10-09"),
                                 (False, "2025-10-09")])
        self.assertEqual(self.chat, ["that was: classic"])

    async def test_a_channel_without_clips_gets_the_chat_line_and_nothing_plays(self) -> None:
        self.assertEqual(await self._shout(), [])
        self.assertEqual(self.chat, ["No clip found for kit"])
        self.assertEqual(len(self.helix.sent("GET", "clips")), 4)


if __name__ == "__main__":
    unittest.main()
