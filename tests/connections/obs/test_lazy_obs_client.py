import unittest

import simpleobsws

from streamer_toolbox.connections.obs.lazy_obs_client import LazyObsClient
from streamer_toolbox.connections.obs.obs_connection_error import ObsConnectionError
from tests.fakes.fake_connectable_obs_client import FakeConnectableObsClient


class TestLazyObsClient(unittest.IsolatedAsyncioTestCase):
    async def test_connects_on_first_call_only(self) -> None:
        fake = FakeConnectableObsClient()
        client = LazyObsClient(fake)
        self.assertEqual(fake.connects, 0)
        await client.call(simpleobsws.Request("GetVersion"))
        await client.call(simpleobsws.Request("GetVersion"))
        self.assertEqual((fake.connects, fake.requests), (1, ["GetVersion", "GetVersion"]))

    async def test_reconnects_after_a_drop(self) -> None:
        fake = FakeConnectableObsClient()
        client = LazyObsClient(fake)
        await client.call(simpleobsws.Request("GetVersion"))
        fake.identified = False  # what simpleobsws does when the socket closes
        await client.call(simpleobsws.Request("GetVersion"))
        self.assertEqual(fake.connects, 2)

    async def test_unreachable_obs_raises_connection_error(self) -> None:
        client = LazyObsClient(FakeConnectableObsClient(reachable=False))
        with self.assertRaisesRegex(ObsConnectionError, "can't reach"):
            await client.call(simpleobsws.Request("GetVersion"))

    async def test_not_identified_raises_and_disconnects(self) -> None:
        fake = FakeConnectableObsClient(identifies=False)
        with self.assertRaisesRegex(ObsConnectionError, "password"):
            await LazyObsClient(fake).call(simpleobsws.Request("GetVersion"))
        self.assertFalse(fake.ws_open)


if __name__ == "__main__":
    unittest.main()
