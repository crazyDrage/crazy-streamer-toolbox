import unittest

from streamer_toolbox.connections.obs.obs_connection_error import ObsConnectionError
from streamer_toolbox.connections.obs.obs_status import ObsStatus
from streamer_toolbox.connections.obs.simpleobsws_connection_checker import SimpleobswsConnectionChecker
from tests.fakes.fake_connectable_obs_client import FakeConnectableObsClient

RESPONSES = {
    "GetVersion": {"obsVersion": "32.0.1", "obsWebSocketVersion": "5.6.2"},
    "GetProfileList": {"currentProfileName": "testing"},
    "GetSceneCollectionList": {"currentSceneCollectionName": "testing"},
    "GetSceneList": {"scenes": [{"sceneName": "bottom"}, {"sceneName": "top"}]},
}


class TestSimpleobswsConnectionChecker(unittest.IsolatedAsyncioTestCase):
    async def test_reads_status_read_only_and_disconnects(self) -> None:
        fake = FakeConnectableObsClient(responses=RESPONSES)
        made: list[tuple[str, str]] = []

        def factory(url: str, password: str) -> FakeConnectableObsClient:
            made.append((url, password))
            return fake

        status = await SimpleobswsConnectionChecker(factory).check("ws://127.0.0.1:4455", "secret")
        self.assertEqual(status, ObsStatus("32.0.1", "5.6.2", "testing", "testing", ("top", "bottom")))
        self.assertEqual(made, [("ws://127.0.0.1:4455", "secret")])
        self.assertTrue(all(r.startswith("Get") for r in fake.requests))
        self.assertFalse(fake.ws_open)

    async def test_wrong_password_raises_and_disconnects(self) -> None:
        fake = FakeConnectableObsClient(identifies=False)
        with self.assertRaises(ObsConnectionError):
            await SimpleobswsConnectionChecker(lambda url, password: fake).check("ws://x", "wrong")
        self.assertFalse(fake.ws_open)


if __name__ == "__main__":
    unittest.main()
