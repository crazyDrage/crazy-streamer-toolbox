import asyncio
import time
import unittest

from streamer_toolbox.connections.tits_connection import TitsConnection
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.events.event_fields import EVENT_FIELDS
from tests.fakes.fake_json_socket_server import FakeJsonSocketServer

ITEMS = [{"ID": "i-1", "name": "Tomato", "encodedImage": ""}, {"ID": "i-2", "name": "Plush"}]
TRIGGERS = [{"ID": "t-1", "name": "Rain"}]


def tits(message: dict, path: str) -> dict:
    """Answers like the API's README: the request's id and type come back, the type as ...Response."""
    kind, data = message["messageType"], message.get("data") or {}
    back = {"apiName": "TITSPublicApi", "apiVersion": "1.0", "timestamp": 1, "requestID": message["requestID"],
            "messageType": kind.replace("Request", "Response")}
    if kind == "TITSItemListRequest":
        back["data"] = {"items": ITEMS}
    elif kind == "TITSTriggerListRequest":
        back["data"] = {"triggers": TRIGGERS}
    elif kind == "TITSThrowItemsRequest":
        back["data"] = {"numberOfThrownItems": data["amountOfThrows"]}
    elif kind == "TITSTriggerActivateRequest" and data["triggerID"] != "t-1":
        back.update(messageType="APIError", data={"message": "no such trigger"})
    return back


async def until(check, timeout: float = 3.0) -> None:
    end = time.monotonic() + timeout
    while not check():
        if time.monotonic() > end:
            raise AssertionError("timed out")
        await asyncio.sleep(0.02)


class TestTitsConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.events = EventBus()
        self.seen: list[tuple[str, dict]] = []

        async def listen(kind: str, data: dict) -> None:
            self.seen.append((kind, data))

        self.events.subscribe(listen)

    def _connection(self, url: str, enabled: bool = True) -> tuple[TitsConnection, ActionRegistry]:
        connection = TitsConnection({"enabled": enabled, "url": url}, self.events, retry_delay=0.05)
        actions = ActionRegistry()
        connection.add_actions(actions)
        return connection, actions

    async def test_items_are_thrown_and_triggers_activated_by_name(self) -> None:
        async with FakeJsonSocketServer(tits) as server:
            connection, actions = self._connection(server.url + "/")
            self.assertEqual((await connection.test(connection.settings)).state, ConnectionState.CONNECTED)
            await connection.start()
            await until(lambda: connection.status.state is ConnectionState.CONNECTED)
            await until(lambda: sorted(server.paths[-2:]) == ["/events", "/websocket"])
            self.assertEqual(await actions.get("tits.throw").options["item"](), ["Plush", "Tomato"])
            self.assertEqual(await actions.get("tits.activate_trigger").options["trigger"](), ["Rain"])
            self.assertEqual(await actions.run("tits.throw", item="tomato", amount=3), {"thrown": 3})
            thrown = server.received[-1]
            self.assertEqual((thrown["apiName"], thrown["data"]["items"], thrown["data"]["amountOfThrows"]),
                             ("TITSPublicApi", ["i-1"], 3))
            await actions.run("tits.activate_trigger", trigger="Rain")
            self.assertEqual(server.received[-1]["data"], {"triggerID": "t-1", "triggerName": "Rain"})
            with self.assertRaisesRegex(KeyError, "no item named"):
                await actions.run("tits.throw", item="Anvil")
            await connection.stop()

    async def test_a_hit_and_a_trigger_start_flows(self) -> None:
        async with FakeJsonSocketServer(tits) as server:
            connection, _ = self._connection(server.url)
            await connection.start()
            await until(lambda: "/events" in server.paths)
            await server.tell({"messageType": "TITSHitEvent", "data": {
                "itemID": "i-1", "itemName": "Tomato", "triggerID": "", "triggerName": "", "strength": 0.4,
                "direction": {"x": 0, "y": 1, "z": 0}}}, "/events")
            await server.tell({"messageType": "TITSTriggerEndedEvent",
                               "data": {"triggerID": "t-1", "triggerName": "Rain"}}, "/events")
            await until(lambda: len(self.seen) == 2)
            self.assertEqual(self.seen[0], ("tits.hit", {"item": "Tomato", "item_id": "i-1", "trigger": "",
                                                         "trigger_id": "", "strength": 0.4}))
            self.assertEqual(self.seen[1], ("tits.trigger_ended", {"trigger": "Rain", "trigger_id": "t-1"}))
            for kind, data in self.seen:
                self.assertEqual(set(data), set(EVENT_FIELDS[kind]))
            await connection.stop()

    async def test_off_or_not_running_is_said_plainly_and_it_comes_back(self) -> None:
        async with FakeJsonSocketServer(tits) as server:
            gone = server.url
        _, off = self._connection(gone, enabled=False)
        with self.assertRaisesRegex(NotConnectedError, "switched off"):
            await off.run("tits.throw", item="Tomato")
        connection, actions = self._connection(gone)
        self.assertIn("can't reach", (await connection.test(connection.settings)).detail)
        await connection.start()
        await until(lambda: connection.status.state is ConnectionState.ERROR)
        self.assertIn("trying again", connection.status.detail)
        with self.assertRaisesRegex(NotConnectedError, "not connected"):
            await actions.run("tits.throw", item="Tomato")
        self.assertEqual(await actions.get("tits.throw").options["item"](), [])
        async with FakeJsonSocketServer(tits) as again:
            connection.configure({"enabled": True, "url": again.url})
            await until(lambda: connection.status.state is ConnectionState.CONNECTED)
            self.assertEqual(await actions.run("tits.throw", item="Plush"), {"thrown": 1})
        await connection.stop()
        self.assertEqual(connection.status.state, ConnectionState.OFF)


if __name__ == "__main__":
    unittest.main()
