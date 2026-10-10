import unittest

from streamer_toolbox.connections.mixitup_connection import MixItUpConnection
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_state import ConnectionState
from tests.connections.mixitup.fake_mix_it_up import CURRENCY_ID, USER_ID, FakeMixItUp


class TestMixItUpActions(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.miu = FakeMixItUp()
        self.connection = MixItUpConnection({"enabled": True}, self.miu.transport())
        await self.connection.start()
        self.actions = ActionRegistry()
        self.connection.add_actions(self.actions)

    async def run_box(self, name: str, **params):
        return await self.actions.run(f"mixitup.{name}", **params)

    async def test_command_picker_is_grouped_by_type(self) -> None:
        groups = await self.actions.get("mixitup.run_command").options["command"]()
        self.assertEqual(groups, {"Chat": {"hammer_bong": "hammer_bong"},
                                  "Action Group": {"desktop_scene_dragon": "desktop_scene_dragon"},
                                  "Pre-Made": {"Magic 8 Ball": "Magic 8 Ball"}})

    async def test_run_command_by_name(self) -> None:
        await self.run_box("run_command", command="hammer_bong", arguments="loud")
        await self.run_box("run_command", command="magic 8 ball", platform="YouTube", ignore_requirements=True)
        self.assertEqual(self.miu.sent("POST"), [
            ("commands/id-hammer", {"Arguments": "loud"}),
            ("commands/id-magic", {"Arguments": "", "Platform": "YouTube", "IgnoreRequirements": True})])

    async def test_unknown_command(self) -> None:
        with self.assertRaisesRegex(LookupError, "no command named 'nope'"):
            await self.run_box("run_command", command="nope")

    async def test_command_on_off_toggle(self) -> None:
        for state in ("off", "on", "toggle"):
            await self.run_box("set_command", command="hammer_bong", state=state)
        self.assertEqual([path for path, _ in self.miu.sent("PATCH")],
                         ["commands/id-hammer/state/0", "commands/id-hammer/state/1", "commands/id-hammer/state/2"])

    async def test_chat(self) -> None:
        await self.run_box("send_chat", message="hi", as_streamer="true")
        await self.run_box("clear_chat")
        self.assertEqual(self.miu.sent("POST"), [
            ("chat/message", {"Message": "hi", "Platform": "All", "SendAsStreamer": True}), ("chat/clear", {})])

    async def test_get_viewer_names_their_currency(self) -> None:
        viewer = await self.run_box("get_user", username="@Viewer")
        self.assertEqual(viewer, {"id": USER_ID, "name": "Viewer", "minutes": 90, "currency": {"rats": 42},
                                  "items": {}})

    async def test_unknown_viewer_is_a_box_error_not_a_broken_connection(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "User 'ghost' not found on platform 'Twitch'"):
            await self.run_box("get_currency", currency="rats", username="ghost")
        self.assertEqual(self.connection.status.state, ConnectionState.CONNECTED)

    async def test_currency(self) -> None:
        self.assertEqual(await self.run_box("get_currency", currency="Rats", username="viewer"), 42)
        self.assertEqual(await self.run_box("add_currency", currency="rats", username="viewer", amount="-2"), 40)
        await self.run_box("set_currency", currency="rats", username="viewer", amount=100)
        self.assertEqual(self.miu.rats, 100)
        self.assertEqual(self.miu.sent("PUT"), [(f"currency/{CURRENCY_ID}/{USER_ID}", {"Amount": 100})])

    async def test_inventory_items_by_inventory_and_name(self) -> None:
        picker = await self.actions.get("mixitup.get_item").options["item"]()
        self.assertEqual(picker, {"Bag": {"Bag · Sword": "Sword"}})
        self.assertEqual(await self.run_box("get_item", item="Bag · Sword", username="viewer"), 1)
        await self.run_box("add_item", item="sword", username="viewer", amount=2)
        self.assertEqual(self.miu.items["id-sword"], 3)
        with self.assertRaisesRegex(LookupError, "no inventory item 'Shield'"):
            await self.run_box("set_item", item="Shield", username="viewer", amount=1)

    async def test_counters(self) -> None:
        self.assertEqual(await self.actions.get("mixitup.get_counter").options["counter"](), ["deaths"])
        self.assertEqual(await self.run_box("add_to_counter", counter="deaths"), 4)
        await self.run_box("set_counter", counter="wins / day", amount=5)  # new: made first, "/" stays in the name
        self.assertEqual(self.miu.counters["wins / day"], 5)
        await self.run_box("reset_counter", counter="deaths")
        self.assertEqual(await self.run_box("get_counter", counter="deaths"), 0)


if __name__ == "__main__":
    unittest.main()
