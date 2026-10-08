import json
import unittest

import httpx

from streamer_toolbox.connections.firebot_connection import FirebotConnection
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError

PRESETS = [{"id": "p-1", "name": "Confetti", "args": ["user"]}, {"id": "p-2", "name": "Lights out", "args": []}]


class TestFirebotConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.asked: list[tuple[str, str, dict | None]] = []
        self.counter = 10
        self.down = False

    def _firebot(self, request: httpx.Request) -> httpx.Response:
        if self.down:
            raise httpx.ConnectError("refused")
        path = request.url.path.removeprefix("/api/v1/")
        body = json.loads(request.content) if request.content else None
        self.asked.append((request.method, path, body))
        if path == "effects/preset":
            return httpx.Response(200, json=PRESETS)
        if path.startswith("effects/preset/"):
            return httpx.Response(200, json={"status": "success"})
        if path == "counters":
            return httpx.Response(200, json=[{"id": "c-1", "name": "Deaths", "value": self.counter}])
        if path == "counters/c-1" and request.method == "GET":
            return httpx.Response(200, json={"id": "c-1", "name": "Deaths", "value": self.counter})
        if path == "counters/c-1":
            old, self.counter = self.counter, body["value"] if body["override"] else self.counter + body["value"]
            return httpx.Response(200, json={"oldValue": old, "newValue": self.counter})
        if path == "custom-variables/mood" and request.method == "GET":
            return httpx.Response(200, json={"name": "mood", "data": "sleepy", "ttl": 0})
        if path == "custom-variables/mood":
            return httpx.Response(200, json={"status": "success"})
        return httpx.Response(404, json={"status": "error", "message": "Not found"})

    def _connection(self, enabled: bool = True) -> tuple[FirebotConnection, ActionRegistry]:
        connection = FirebotConnection({"enabled": enabled}, transport=httpx.MockTransport(self._firebot))
        actions = ActionRegistry()
        connection.add_actions(actions)
        return connection, actions

    async def test_effect_lists_run_by_name_with_their_arguments(self) -> None:
        connection, actions = self._connection()
        await connection.start()
        self.assertEqual((connection.status.state, connection.status.facts),
                         (ConnectionState.CONNECTED, (("Preset effect lists", "2"),)))
        self.assertEqual(await actions.get("firebot.run_preset").options["preset"](), ["Confetti", "Lights out"])
        await actions.run("firebot.run_preset", preset="confetti", args={"user": "ann"}, user="ann")
        self.assertEqual(self.asked[-1], ("POST", "effects/preset/p-1/run",
                                          {"args": {"user": "ann"}, "username": "ann"}))
        await actions.run("firebot.run_preset", preset="Lights out", wait=True)
        self.assertEqual(self.asked[-1], ("POST", "effects/preset/p-2", {"args": {}}))
        with self.assertRaisesRegex(KeyError, "no preset effect list named"):
            await actions.run("firebot.run_preset", preset="Rain")

    async def test_variables_and_counters_are_read_and_set(self) -> None:
        _, actions = self._connection()
        self.assertEqual(await actions.run("firebot.get_variable", name="mood"), {"value": "sleepy"})
        await actions.run("firebot.set_variable", name="mood", value="awake", seconds=60)
        self.assertEqual(self.asked[-1], ("POST", "custom-variables/mood", {"data": "awake", "ttl": 60}))
        self.assertEqual(await actions.get("firebot.get_counter").options["counter"](), ["Deaths"])
        self.assertEqual(await actions.run("firebot.get_counter", counter="Deaths"), {"value": 10})
        self.assertEqual(await actions.run("firebot.set_counter", counter="Deaths", value="2", add=True),
                         {"value": 12})
        self.assertEqual(await actions.run("firebot.set_counter", counter="Deaths", value=0), {"value": 0})
        with self.assertRaisesRegex(RuntimeError, "Firebot: Not found"):
            await actions.run("firebot.get_variable", name="missing")

    async def test_off_or_not_running_is_said_plainly_and_it_comes_back(self) -> None:
        _, off = self._connection(enabled=False)
        with self.assertRaisesRegex(NotConnectedError, "switched off"):
            await off.run("firebot.run_preset", preset="Confetti")
        self.down = True
        connection, actions = self._connection()
        await connection.start()
        self.assertEqual(connection.status.detail, "can't reach Firebot: is it running?")
        with self.assertRaisesRegex(NotConnectedError, "is it running"):
            await actions.run("firebot.run_preset", preset="Confetti")
        self.assertEqual(await actions.get("firebot.run_preset").options["preset"](), [])
        self.down = False
        await actions.run("firebot.run_preset", preset="Confetti")
        self.assertEqual(connection.status.state, ConnectionState.CONNECTED)


if __name__ == "__main__":
    unittest.main()
