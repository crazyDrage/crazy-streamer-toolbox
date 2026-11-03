import unittest

import simpleobsws

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.config.obs_config import ObsConfig
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.connections.obs_connection import ObsConnection
from tests.fakes.fake_connectable_obs_client import FakeConnectableObsClient
from tests.fakes.fake_video_probe import FakeVideoProbe

RESPONSES = {
    "GetVersion": {"obsVersion": "32.2.2", "obsWebSocketVersion": "5.7.4"},
    "GetProfileList": {"currentProfileName": "testing"},
    "GetSceneCollectionList": {"currentSceneCollectionName": "testing"},
    "GetSceneList": {"scenes": [{"sceneName": "toolbox_test"}]},
    "GetCurrentProgramScene": {"currentProgramSceneName": "toolbox_test"},
}


class TestObsConnection(unittest.IsolatedAsyncioTestCase):
    def _connection(self, fake: FakeConnectableObsClient, enabled: bool = True) -> ObsConnection:
        return ObsConnection(ObsConfig(enabled=enabled), FakeVideoProbe({}), lambda url, password: fake)

    async def test_start_connects_and_shows_facts(self) -> None:
        fake = FakeConnectableObsClient(responses=RESPONSES)
        connection = self._connection(fake)
        await connection.start()
        self.assertEqual(connection.status.state, ConnectionState.CONNECTED)
        self.assertIn(("Scene collection", "testing"), connection.status.facts)
        self.assertTrue(fake.ws_open)  # stays connected
        await connection.stop()
        self.assertFalse(fake.ws_open)

    async def test_obs_down_at_start_then_back(self) -> None:
        fake = FakeConnectableObsClient(reachable=False, responses=RESPONSES)
        connection = self._connection(fake)
        await connection.start()
        self.assertEqual(connection.status.state, ConnectionState.ERROR)
        fake._reachable = True  # OBS was started later
        await connection.call(simpleobsws.Request("GetVersion"))
        self.assertEqual(connection.status.state, ConnectionState.CONNECTED)

    async def test_switch_scene(self) -> None:
        fake = FakeConnectableObsClient(responses=RESPONSES)
        connection = self._connection(fake)
        await connection.switch_scene("Just_chatting")
        self.assertEqual(fake.requests[-1], "SetCurrentProgramScene")

    async def test_the_scene_boxes_run_by_name(self) -> None:
        fake = FakeConnectableObsClient(responses=RESPONSES)
        connection = self._connection(fake)
        actions = ActionRegistry()
        connection.add_actions(actions)
        await actions.run("obs.switch_scene", scene="Just_chatting")
        self.assertEqual(fake.calls[-1], ("SetCurrentProgramScene", {"sceneName": "Just_chatting"}))
        self.assertEqual(await actions.run("obs.get_current_scene"), "toolbox_test")
        self.assertEqual(await actions.get("obs.switch_scene").options["scene"](), ["toolbox_test"])

    async def test_switched_off_refuses_calls(self) -> None:
        connection = self._connection(FakeConnectableObsClient(), enabled=False)
        with self.assertRaises(NotConnectedError):
            await connection.call(simpleobsws.Request("GetVersion"))


if __name__ == "__main__":
    unittest.main()
