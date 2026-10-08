import unittest

from streamer_toolbox.connections.obs.obs_request_actions import ObsRequestActions
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from tests.fakes.fake_connectable_obs_client import FakeConnectableObsClient

RESPONSES = {
    "GetVersion": {"availableRequests": ["SetCurrentProgramScene", "GetStats", "GetVersion"]},
    "GetStats": {"cpuUsage": 3.5},
}


class TestObsRequestActions(unittest.IsolatedAsyncioTestCase):
    async def test_sends_any_request_with_json_data(self) -> None:
        fake = FakeConnectableObsClient(responses=RESPONSES)
        actions = ActionRegistry()
        ObsRequestActions(fake.call).add_to(actions)
        self.assertEqual(await actions.run("obs.request", request="GetStats"), {"cpuUsage": 3.5})
        await actions.run("obs.request", request="SetCurrentProgramScene", data='{"sceneName": "desktop"}')
        await actions.run("obs.request", request="SetCurrentProgramScene", data={"sceneName": "Just_chatting"})
        self.assertEqual(fake.calls, [("GetStats", {}), ("SetCurrentProgramScene", {"sceneName": "desktop"}),
                                      ("SetCurrentProgramScene", {"sceneName": "Just_chatting"})])
        for bad in ("{sceneName}", "[1]"):
            with self.assertRaises(ValueError):
                await actions.run("obs.request", request="SetCurrentProgramScene", data=bad)
        self.assertTrue(actions.get("obs.request").flow_only)
        self.assertEqual(await actions.get("obs.request").options["request"](),
                         {"General": {"GetStats": "GetStats", "GetVersion": "GetVersion"},
                          "Scenes": {"SetCurrentProgramScene": "SetCurrentProgramScene"}})


if __name__ == "__main__":
    unittest.main()
