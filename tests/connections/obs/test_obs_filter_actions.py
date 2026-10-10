import unittest

from streamer_toolbox.connections.obs.obs_filter_actions import ObsFilterActions
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from tests.fakes.fake_obs_script import FakeObsScript


class TestObsFilterActions(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.obs = FakeObsScript({
            "GetSourceFilter": {"filterEnabled": True},
            "GetSceneList": {"scenes": [{"sceneName": "desktop"}]},
            "GetInputList": {"inputs": [{"inputName": "cam"}, {"inputName": "mic"}]},
            "GetSourceFilterList": [{"filters": []}, {"filters": [{"filterName": "Blur"}]}, {"filters": []}]})
        self.actions = ActionRegistry()
        ObsFilterActions(ObsRequests(self.obs.call)).add_to(self.actions)

    async def test_on_off_toggle(self) -> None:
        self.assertFalse(await self.actions.run("obs.set_filter", source="cam", filter="Blur"))  # it was on
        self.assertTrue(await self.actions.run("obs.set_filter", source="cam", filter="Blur", state="on"))
        self.assertFalse(await self.actions.run("obs.set_filter", source="cam", filter="Blur", state="off"))
        self.assertEqual([d["filterEnabled"] for d in self.obs.sent("SetSourceFilterEnabled")], [False, True, False])

    async def test_filter_picker_by_source(self) -> None:
        picker = await self.actions.get("obs.set_filter").options["filter"]()
        self.assertEqual(picker, {"cam": {"Blur": "Blur"}})


if __name__ == "__main__":
    unittest.main()
