import asyncio
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.connections.vtube_studio.vts_position import VtsPosition
from streamer_toolbox.connections.vtube_studio.vts_position_store import VtsPositionStore
from streamer_toolbox.connections.vts_connection import VtsConnection
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.events.event_bus import EventBus
from tests.fakes.fake_vts_server import FakeVtsServer


class TestVtsConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        folder = Path(self._dir.name)
        self.token = folder / "vts_token.txt"
        self.positions = VtsPositionStore(folder / "vts_positions.toml")

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _paired(self, server: FakeVtsServer) -> VtsConnection:
        self.token.write_text("paired", encoding="utf-8")
        server.valid_tokens.add("paired")
        return self._connection(server)

    def _connection(self, server: FakeVtsServer) -> VtsConnection:
        return VtsConnection({"enabled": True, "url": server.url}, self.token, self.positions)

    async def test_toolbox_start_never_pops_up_the_allow_dialog(self) -> None:
        async with FakeVtsServer() as server:
            connection = self._connection(server)
            await connection.start()
        self.assertEqual(connection.status.state, ConnectionState.ERROR)
        self.assertIn("press Connect", connection.status.detail)
        self.assertNotIn("AuthenticationTokenRequest", [kind for kind, _ in server.requests])

    async def test_connect_asks_for_token_and_keeps_it(self) -> None:
        async with FakeVtsServer() as server:
            connection = self._connection(server)
            status = await connection.test({"url": server.url})
            self.assertIn(("Model", "Dragon"), status.facts)
            await connection.start()  # now paired: no popup
            self.assertEqual(connection.status.state, ConnectionState.CONNECTED)
            await connection.stop()
        self.assertEqual(self.token.read_text(encoding="utf-8"), "new-token")
        self.assertEqual([kind for kind, _ in server.requests].count("AuthenticationTokenRequest"), 1)

    async def test_saved_token_is_used_without_popup(self) -> None:
        self.token.write_text("old-token", encoding="utf-8")
        async with FakeVtsServer(valid_tokens=("old-token",)) as server:
            connection = self._connection(server)
            await connection.start()
            await connection.stop()
        self.assertNotIn("AuthenticationTokenRequest", [kind for kind, _ in server.requests])

    async def test_keep_alive_connects_once_vts_is_ready(self) -> None:
        self.token.write_text("paired", encoding="utf-8")
        async with FakeVtsServer() as server:
            connection = VtsConnection({"enabled": True, "url": server.url}, self.token, self.positions, events=EventBus())
            await connection.start()  # token not known yet: as if VTS wasn't up
            self.assertEqual(connection.status.state, ConnectionState.ERROR)
            server.valid_tokens.add("paired")
            await connection.keep_alive()
            self.assertEqual(connection.status.state, ConnectionState.CONNECTED)
            self.assertIn("ModelLoadedEvent", [data.get("eventName") for kind, data in server.requests])
            await connection.stop()
        self.assertNotIn("AuthenticationTokenRequest", [kind for kind, _ in server.requests])

    async def test_keep_alive_notices_vts_was_closed(self) -> None:
        async with FakeVtsServer() as server:
            connection = self._paired(server)
            await connection.start()
            self.assertEqual(connection.status.state, ConnectionState.CONNECTED)
            for ws in list(server._clients):
                await ws.close()
            await asyncio.sleep(0.05)
        await connection.keep_alive()
        self.assertEqual(connection.status.state, ConnectionState.ERROR)
        await connection.stop()

    async def test_move_model_keeps_empty_values(self) -> None:
        async with FakeVtsServer() as server:
            connection = self._paired(server)
            actions = ActionRegistry()
            connection.add_actions(actions)
            await connection.start()
            await actions.run("vts.move_model", x=-0.3, size="", seconds=0.5)
            move = [data for kind, data in server.requests if kind == "MoveModelRequest"][-1]
            await connection.stop()
        self.assertEqual(move, {"timeInSeconds": 0.5, "valuesAreRelativeToModel": False, "positionX": -0.3,
                                "positionY": -0.5, "rotation": 0.0, "size": -50.0})

    async def test_play_animation_moves_from_where_the_model_is(self) -> None:
        async with FakeVtsServer() as server:
            connection = self._paired(server)
            actions = ActionRegistry()
            connection.add_actions(actions)
            await connection.start()
            await actions.run("vts.play_animation", animation={"relative": True, "steps": [
                {"x": 0.2, "y": 0.0, "rotation": 10.0, "size": 0.0, "seconds": 0.0, "wait": 0.0}]},
                repeat="1", back_to_start="true", back_seconds=0)
            moves = [data for kind, data in server.requests if kind == "MoveModelRequest"]
            await connection.stop()
        self.assertEqual(len(moves), 2)
        self.assertAlmostEqual(moves[0]["positionX"], 0.3)
        self.assertEqual(moves[0]["rotation"], 10.0)
        self.assertFalse(moves[0]["valuesAreRelativeToModel"])
        self.assertEqual((moves[1]["positionX"], moves[1]["positionY"]), (0.1, -0.5))
        self.assertEqual(actions.get("vts.play_animation").editors, {"animation": "vts_animation"})

    async def test_loop_forever_runs_in_the_background_until_stopped(self) -> None:
        loop = {"relative": True, "steps": [
            {"x": 0.2, "y": 0.0, "rotation": 0.0, "size": 0.0, "seconds": 0.0, "wait": 0.02},
            {"x": 0.0, "y": 0.0, "rotation": 0.0, "size": 0.0, "seconds": 0.0, "wait": 0.02}]}
        async with FakeVtsServer() as server:
            connection = self._paired(server)
            actions = ActionRegistry()
            connection.add_actions(actions)
            await connection.start()
            await asyncio.wait_for(actions.run("vts.play_animation", animation=loop, loop_forever="true"), 1)
            await asyncio.sleep(0.2)  # the box returned at once; the loop goes on
            looped = len([1 for kind, _ in server.requests if kind == "MoveModelRequest"])
            self.assertTrue(await actions.run("vts.stop_animation", back_to_start=True, back_seconds=0))
            moves = [data for kind, data in server.requests if kind == "MoveModelRequest"]
            await asyncio.sleep(0.1)
            after = len([1 for kind, _ in server.requests if kind == "MoveModelRequest"])
            self.assertFalse(await actions.run("vts.stop_animation"))
            await connection.stop()
        self.assertGreater(looped, 4)
        self.assertEqual((moves[-1]["positionX"], moves[-1]["positionY"]), (0.1, -0.5))  # back to the start
        self.assertEqual(after, len(moves))  # stopped for good

    async def test_a_new_animation_stops_the_one_playing(self) -> None:
        slow = {"relative": True, "steps": [
            {"x": 0.2, "y": 0.0, "rotation": 0.0, "size": 0.0, "seconds": 0.0, "wait": 5.0}]}
        async with FakeVtsServer() as server:
            connection = self._paired(server)
            actions = ActionRegistry()
            connection.add_actions(actions)
            await connection.start()
            first = asyncio.create_task(actions.run("vts.play_animation", animation=slow))
            await asyncio.sleep(0.1)
            await asyncio.wait_for(actions.run("vts.play_animation", animation=slow, repeat=1,
                                               loop_forever=True), 1)
            await asyncio.wait_for(first, 1)  # ended (stopped), without an error
            await connection.stop()

    async def test_move_model_by_is_relative(self) -> None:
        async with FakeVtsServer() as server:
            connection = self._paired(server)
            actions = ActionRegistry()
            connection.add_actions(actions)
            await connection.start()
            await actions.run("vts.move_model_by", x="-0.2", y="", seconds=0.5)
            move = [data for kind, data in server.requests if kind == "MoveModelRequest"][-1]
            await connection.stop()
        self.assertEqual(move, {"timeInSeconds": 0.5, "valuesAreRelativeToModel": True, "positionX": -0.2,
                                "positionY": 0.0, "rotation": 0.0, "size": 0.0})

    async def test_vts_events_become_flow_events(self) -> None:
        events, seen = EventBus(), []

        async def record(kind, data):
            seen.append((kind, data))

        events.subscribe(record)
        async with FakeVtsServer() as server:
            self.token.write_text("paired", encoding="utf-8")
            server.valid_tokens.add("paired")
            connection = VtsConnection({"enabled": True, "url": server.url}, self.token, self.positions, events=events)
            await connection.start()
            await server.send_event("TrackingStatusChangedEvent", {"faceFound": False, "leftHandFound": True,
                                                                   "rightHandFound": False})
            await server.send_event("HotkeyTriggeredEvent", {"hotkeyName": "Tail", "hotkeyID": "h1",
                                                             "hotkeyAction": "TriggerAnimation", "modelName": "Dragon"})
            for _ in range(50):
                if len(seen) == 2:
                    break
                await asyncio.sleep(0.02)
            subscribed = [d["eventName"] for k, d in server.requests if k == "EventSubscriptionRequest"]
            await connection.stop()
        self.assertEqual(seen[0], ("vts.tracking", {"face": False, "left_hand": True, "right_hand": False}))
        self.assertEqual(seen[1][1]["hotkey"], "Tail")
        self.assertIn("TrackingStatusChangedEvent", subscribed)

    async def test_denied_popup_is_explained(self) -> None:
        async with FakeVtsServer(allow=False) as server:
            status = await self._connection(server).test({"url": server.url})
        self.assertEqual(status.detail,
                         "You clicked Deny in VTube Studio. Press Connect to be asked again.")

    async def test_save_and_move_to_position_per_model(self) -> None:
        async with FakeVtsServer() as server:
            connection = self._paired(server)
            actions = ActionRegistry()
            connection.add_actions(actions)
            await connection.start()
            await actions.run("vts.save_position", position="just_chatting")
            server.model["modelPosition"] = {"positionX": 0.9, "positionY": 0.9, "rotation": 0.0, "size": 0.0}
            await actions.run("vts.move_to_position", position="just_chatting", seconds=0.5)
            move = [data for kind, data in server.requests if kind == "MoveModelRequest"][-1]
            await connection.stop()
        self.assertEqual(self.positions.get("Dragon", "just_chatting"), VtsPosition(0.1, -0.5, 0.0, -50.0))
        self.assertEqual((move["positionX"], move["timeInSeconds"], move["valuesAreRelativeToModel"]),
                         (0.1, 0.5, False))

    async def test_unknown_position_is_a_clear_error(self) -> None:
        async with FakeVtsServer() as server:
            connection = self._paired(server)
            await connection.start()
            with self.assertRaisesRegex(KeyError, "no saved position 'nope' for model 'Dragon'"):
                await connection.move_to_position("nope")
            await connection.stop()

    async def test_trigger_hotkey_by_name(self) -> None:
        async with FakeVtsServer() as server:
            connection = self._paired(server)
            actions = ActionRegistry()
            connection.add_actions(actions)
            await actions.run("vts.trigger_hotkey", hotkey="tail on")  # connects on demand
            await connection.stop()
        self.assertIn(("HotkeyTriggerRequest", {"hotkeyID": "tail on"}), server.requests)

    async def test_model_loaded_event_goes_on_the_event_bus(self) -> None:
        events, seen = EventBus(), []

        async def record(kind, data):
            seen.append((kind, data))

        events.subscribe(record)
        async with FakeVtsServer() as server:
            self.token.write_text("paired", encoding="utf-8")
            server.valid_tokens.add("paired")
            connection = VtsConnection({"enabled": True, "url": server.url}, self.token, self.positions, events=events)
            await connection.start()
            self.assertIn("ModelLoadedEvent", server.subscribed)
            await server.send_event("ModelLoadedEvent", {"modelLoaded": False, "modelName": "", "modelID": ""})
            await server.send_event("ModelLoadedEvent", {"modelLoaded": True, "modelName": "Dragon", "modelID": "d1"})
            for _ in range(50):
                if seen:
                    break
                await asyncio.sleep(0.02)
            await events.wait_idle()
            await connection.stop()
        self.assertEqual(seen, [("vts.model_loaded", {"model": "Dragon", "model_id": "d1"})])

    async def test_items_and_expressions(self) -> None:
        async with FakeVtsServer() as server:
            connection = self._paired(server)
            actions = ActionRegistry()
            connection.add_actions(actions)
            self.assertEqual(await actions.run("vts.load_item", file="fan.png", x="0.2", y=-0.5), "i2")
            self.assertTrue(await actions.run("vts.item_in_scene", file="MINI_LIZARD.png"))
            self.assertTrue(await actions.run("vts.item_in_scene", file="mini_lizard"))  # item scene name
            self.assertFalse(await actions.run("vts.item_in_scene", file="fan.png"))
            await actions.run("vts.move_item", instance="i2", x=0.3, y=0.4, seconds="0.5")
            self.assertEqual(await actions.run("vts.remove_items"), 1)
            self.assertEqual(await actions.get("vts.load_item").options["file"](), ["fan.png", "mini_lizard.png"])
            await actions.run("vts.set_expression", expression="fire_arm.exp3.json", active="false")
            self.assertTrue(await actions.run("vts.expression_active", expression="fire_arm.exp3.json"))
            self.assertFalse(await actions.run("vts.expression_active", expression="sad.exp3.json"))
            await connection.stop()
        requests = dict(server.requests)
        self.assertEqual((requests["ItemLoadRequest"]["positionX"], requests["ItemLoadRequest"]["positionY"]),
                         (0.2, -0.5))
        self.assertEqual(requests["ItemMoveRequest"]["itemsToMove"][0]["itemInstanceID"], "i2")
        self.assertTrue(requests["ItemUnloadRequest"]["unloadAllLoadedByThisPlugin"])
        self.assertEqual(requests["ExpressionActivationRequest"], {"expressionFile": "fire_arm.exp3.json",
                                                                   "active": False})

    async def test_position_knows_its_model_and_can_load_it_first(self) -> None:
        async with FakeVtsServer() as server:
            connection = self._paired(server)
            actions = ActionRegistry()
            connection.add_actions(actions)
            saved = await actions.run("vts.get_model_position")
            self.assertEqual(saved, {"x": 0.1, "y": -0.5, "rotation": 0.0, "size": -50.0, "model": "Dragon"})
            await actions.run("vts.load_model", model="Human")
            await actions.run("vts.move_model_to", position=saved, seconds=0)  # moves Human, no model switch
            self.assertEqual(server.model["modelName"], "Human")
            await actions.run("vts.move_model_to", position={**saved, "x": 0.7}, seconds=0, load_model="true")
            self.assertEqual(server.model["modelName"], "Dragon")
            self.assertEqual(server.model["modelPosition"]["positionX"], 0.7)
            await actions.run("vts.move_model_to", position={"x": 0, "y": 0, "rotation": 0, "size": 0},
                              load_model=True)  # an old position without a model just moves
            await connection.stop()
        self.assertEqual([k for k, _ in server.requests].count("ModelLoadRequest"), 2)

    async def test_load_model_waits_until_vts_shows_it(self) -> None:
        async with FakeVtsServer() as server:
            server.load_seconds = 0.6
            connection = self._paired(server)
            actions = ActionRegistry()
            connection.add_actions(actions)
            await actions.run("vts.load_model", model="Human")
            self.assertEqual(server.model["modelName"], "Human")  # loaded by the time the box ends
            await actions.run("vts.load_model", model="Dragon", wait_until_loaded="false")
            self.assertFalse(server.model["modelLoaded"])  # not waited: still loading
            await asyncio.sleep(0.8)
            with self.assertRaises(TimeoutError):
                server.load_seconds = 5
                await actions.run("vts.load_model", model="Human", seconds=0.5)
            await connection.stop()

    async def test_record_a_pin_spot_by_clicking_the_model_then_pin_there(self) -> None:
        click = {"modelLoaded": True, "loadedModelName": "Dragon", "modelWasClicked": True, "artMeshHits": [
            {"artMeshOrder": 1, "hitInfo": {"modelID": "d1", "artMeshID": "face_skin", "vertexID1": 1,
                                            "vertexID2": 2, "vertexID3": 3, "vertexWeight1": 0.2,
                                            "vertexWeight2": 0.3, "vertexWeight3": 0.5}},
            {"artMeshOrder": 0, "hitInfo": {"modelID": "d1", "artMeshID": "hair_right6", "vertexID1": 80,
                                            "vertexID2": 76, "vertexID3": 75, "vertexWeight1": 0.47,
                                            "vertexWeight2": 0.08, "vertexWeight3": 0.45}}]}
        async with FakeVtsServer() as server:
            connection = self._paired(server)
            actions = ActionRegistry()
            connection.add_actions(actions)
            recording = asyncio.create_task(actions.run("vts.record_pin_spot", seconds=5))
            while "ModelClickedEvent" not in server.subscribed:
                await asyncio.sleep(0.01)
            await server.send_event("ModelClickedEvent", click)
            spot = await recording
            self.assertEqual(spot, {"model": "Dragon", "model_id": "d1", "art_mesh": "hair_right6",
                                    "vertices": [80, 76, 75], "weights": [0.47, 0.08, 0.45]})  # the topmost mesh
            self.assertTrue(await actions.run("vts.pin_item", instance="i2", saved_spot=spot))
            with self.assertRaisesRegex(TimeoutError, "no click"):
                await actions.run("vts.record_pin_spot", seconds=0.1)
            with self.assertRaisesRegex(ValueError, "Record pin spot"):
                await actions.run("vts.pin_item", instance="i2", saved_spot={"x": 1})
            self.assertEqual(actions.get("vts.pin_item").capture, "vts.record_pin_spot:saved_spot")
            await connection.stop()
        pin = [data for kind, data in server.requests if kind == "ItemPinRequest"][0]
        self.assertEqual((pin["vertexPinType"], pin["pinInfo"]), ("Provided", {
            "modelID": "d1", "artMeshID": "hair_right6", "angle": 0, "size": 0, "vertexID1": 80, "vertexID2": 76,
            "vertexID3": 75, "vertexWeight1": 0.47, "vertexWeight2": 0.08, "vertexWeight3": 0.45}))
        unsubscribed = [d for k, d in server.requests if k == "EventSubscriptionRequest" and not d["subscribe"]]
        self.assertEqual(len(unsubscribed), 2)  # after the click and after the timeout

    async def test_pin_with_an_angle_and_a_size_and_load_and_pin_in_one(self) -> None:
        async with FakeVtsServer() as server:
            connection = self._paired(server)
            actions = ActionRegistry()
            connection.add_actions(actions)
            await actions.run("vts.pin_item", instance="i2", pin_to="model part", art_mesh="head", angle="45",
                              angle_from="spot", size=0.2)
            with self.assertRaisesRegex(ValueError, "angle_from"):
                await actions.run("vts.pin_item", instance="i2", pin_to="model part", art_mesh="head", angle=1,
                                  angle_from="moon")
            added = await actions.run("vts.add_pinned_item", file="fan.png", pin_to="model part", art_mesh="head",
                                      size=0.4)
            self.assertEqual(added, {"instance": "i2", "pinned": True})
            self.assertEqual(await actions.get("vts.add_pinned_item").options["angle_from"](),
                             ["item", "model", "screen", "spot"])
            await connection.stop()
        first, second = [data for kind, data in server.requests if kind == "ItemPinRequest"]
        self.assertEqual((first["angleRelativeTo"], first["sizeRelativeTo"], first["pinInfo"]["angle"],
                          first["pinInfo"]["size"]), ("RelativeToPinPosition", "RelativeToWorld", 45.0, 0.2))
        self.assertEqual((second["angleRelativeTo"], second["sizeRelativeTo"], second["pinInfo"]["angle"],
                          second["itemInstanceID"]), ("RelativeToModel", "RelativeToCurrentItemSize", 0.0, "i2"))
        loaded = dict(server.requests)["ItemLoadRequest"]
        self.assertEqual((loaded["fileName"], loaded["size"]), ("fan.png", 0.4))

    async def test_pin_to_chooses_between_the_exact_spot_and_a_model_part(self) -> None:
        spot = {"model_id": "m1", "art_mesh": "horn", "vertices": [32, 4, 3], "weights": [0.5, 0.1, 0.4]}
        async with FakeVtsServer() as server:
            connection = self._paired(server)
            actions = ActionRegistry()
            connection.add_actions(actions)
            await actions.run("vts.pin_item", instance="i2", pin_to="model part", saved_spot=spot, art_mesh="head")
            await actions.run("vts.pin_item", instance="i2", saved_spot=spot, art_mesh="head")
            with self.assertRaisesRegex(ValueError, "no exact spot"):
                await actions.run("vts.add_pinned_item", file="fan.png", art_mesh="head")
            with self.assertRaisesRegex(ValueError, "pin_to"):
                await actions.run("vts.pin_item", instance="i2", pin_to="nose", art_mesh="head")
            for name in ("vts.pin_item", "vts.add_pinned_item"):
                action = actions.get(name)
                self.assertEqual(await action.options["pin_to"](), ["exact spot", "model part"])
                self.assertEqual([f for f in ("saved_spot", "art_mesh", "spot") if action.shows(f, {})],
                                 ["saved_spot"])
                self.assertEqual([f for f in ("saved_spot", "art_mesh", "spot")
                                  if action.shows(f, {"pin_to": "model part"})], ["art_mesh", "spot"])
            await connection.stop()
        pins = [data for kind, data in server.requests if kind == "ItemPinRequest"]
        self.assertEqual([(pin["vertexPinType"], pin["pinInfo"]["artMeshID"]) for pin in pins],
                         [("Center", "head"), ("Provided", "horn")])
        self.assertNotIn("ItemLoadRequest", dict(server.requests))  # no spot: nothing was loaded

    async def test_pin_and_unpin_item(self) -> None:
        async with FakeVtsServer() as server:
            connection = self._paired(server)
            actions = ActionRegistry()
            connection.add_actions(actions)
            self.assertTrue(await actions.run("vts.pin_item", instance="i2", pin_to="model part",
                                              art_mesh="head"))
            self.assertFalse(await actions.run("vts.unpin_item", instance="i2"))
            with self.assertRaisesRegex(ValueError, "spot must be"):
                await actions.run("vts.pin_item", instance="i2", pin_to="model part", spot="left ear")
            self.assertEqual(await actions.get("vts.pin_item").options["art_mesh"](), ["arm_l", "Hair_front", "head"])
            self.assertEqual(await actions.get("vts.pin_item").options["spot"](), ["center", "random"])
            await connection.stop()
        pins = [data for kind, data in server.requests if kind == "ItemPinRequest"]
        self.assertEqual(pins[0]["vertexPinType"], "Center")
        self.assertEqual(pins[0]["pinInfo"]["artMeshID"], "head")
        self.assertEqual(pins[1], {"pin": False, "itemInstanceID": "i2"})


if __name__ == "__main__":
    unittest.main()
