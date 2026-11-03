import tempfile
import unittest
from pathlib import Path
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.text_actions import TextActions
from streamer_toolbox.core.flows.flow_pack import FlowPack
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.logic_actions import LogicActions
from streamer_toolbox.core.system.time_actions import TimeActions
from streamer_toolbox.core.variables.variable_store import VariableStore

FILE = Path(__file__).parents[3] / "src" / "streamer_toolbox" / "connections" / "twitch" / "default_flows.flows.toml"


class TestTwitchDefaultFlows(unittest.IsolatedAsyncioTestCase):
    """Twitch's default flows run from their trigger to the chat message (Twitch's boxes are stand-ins here):
    their wires and the values they read are right."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.chat: list[str] = []
        self.shoutouts: list[str] = []
        self.channel: dict[str, Any] = {"live": True, "uptime_seconds": 4980}
        actions = ActionRegistry()
        variables = VariableStore(Path(self._dir.name) / "variables.json")
        LogicActions(variables).add_to(actions)
        TimeActions().add_to(actions)
        TextActions().add_to(actions)
        actions.add("twitch.send_chat", self._say, "")
        actions.add("twitch.shoutout", self._shout, "")
        actions.add("twitch.get_user", self._user, "")
        actions.add("twitch.get_channel", self._channel, "")
        actions.add("twitch.create_clip", self._clip, "")
        actions.add("twitch.create_marker", self._marker, "")
        self.markers: list[str] = []
        self.runner = FlowRunner(actions, variables)
        self.flows = {f.name: f for f in FlowPack.from_text(FILE.read_text(encoding="utf-8")).flows}

    def tearDown(self) -> None:
        self._dir.cleanup()

    async def _say(self, message: str) -> None:
        self.chat.append(message)

    async def _shout(self, user: str) -> None:
        self.shoutouts.append(user)

    async def _user(self, user: str) -> dict[str, str]:
        return {"name": user.lstrip("@").capitalize()}

    async def _channel(self) -> dict[str, Any]:
        return self.channel

    async def _clip(self) -> dict[str, str]:
        return {"id": "Abc", "url": "https://clips.twitch.tv/Abc", "edit_url": ""}

    async def _marker(self, description: str = "") -> str:
        self.markers.append(description)
        return "m1"

    async def _run(self, name: str, event: dict[str, Any]) -> None:
        flow = self.flows[name]
        await self.runner.run(flow, event, start=flow.triggers[0].id)

    async def test_follow_raid_cheer(self) -> None:
        await self._run("twitch_thank_follow", {"user": "Kit"})
        await self._run("twitch_thank_raid", {"user": "Vex", "user_login": "vex", "viewers": 12})
        await self._run("twitch_thank_cheer", {"user": "Kit", "bits": 100})
        self.assertEqual(self.chat, ["Thanks for the follow, Kit!",
                                     "Vex is raiding with 12 viewers! Thank you, and welcome everyone!",
                                     "Thanks for the 100 Bits, Kit!"])
        self.assertEqual(self.shoutouts, ["vex"])

    async def test_so(self) -> None:
        await self._run("twitch_so_command", {"user": "Mod", "args": "@kit", "role": "mod"})
        self.assertEqual(self.chat, ["Go check out Kit: https://twitch.tv/Kit"])
        self.assertEqual(self.shoutouts, ["Kit"])

    async def test_uptime_live_and_not(self) -> None:
        await self._run("twitch_uptime_command", {"user": "Kit"})
        self.channel = {"live": False, "uptime_seconds": 0}
        await self._run("twitch_uptime_command", {"user": "Kit"})
        self.assertEqual(self.chat, ["Live for 1 h 23 min", "Not live right now."])

    async def test_clip_and_marker(self) -> None:
        await self._run("twitch_clip_command", {"user": "Kit", "command": "!clip"})
        await self._run("twitch_marker_command", {"user": "Mod", "args": "funny fall", "role": "mod"})
        self.assertEqual(self.chat, ["Clipped by Kit: https://clips.twitch.tv/Abc", "Marker set."])
        self.assertEqual(self.markers, ["funny fall"])
        self.assertEqual(self.flows["twitch_clip_command"].cooldown, 30)


if __name__ == "__main__":
    unittest.main()
