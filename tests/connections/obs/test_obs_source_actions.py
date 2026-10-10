import unittest

from streamer_toolbox.connections.obs.obs_source_actions import ObsSourceActions
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from tests.fakes.fake_connectable_obs_client import FakeConnectableObsClient

RESPONSES = {
    "GetSceneItemId": {"sceneItemId": 7},
    "GetInputVolume": {"inputVolumeMul": 0.8, "inputVolumeDb": -1.9},
    "GetSceneList": {"scenes": [{"sceneName": "Just_chatting"}, {"sceneName": "desktop"}]},
    "GetSceneItemList": {"sceneItems": [{"sourceName": "vtube_model"}, {"sourceName": "ghost_vtube_model"}]},
    "GetInputList": {"inputs": [{"inputName": "Main mic"}, {"inputName": "Desktop Audio"}]},
}


class TestObsSourceActions(unittest.IsolatedAsyncioTestCase):
    async def test_visibility_volume_and_choices(self) -> None:
        fake = FakeConnectableObsClient(responses=RESPONSES)
        actions = ActionRegistry()
        ObsSourceActions(fake.call).add_to(actions)
        await actions.run("obs.set_source_visible", scene="desktop", source="ghost_vtube_model", visible="false")
        await actions.run("obs.set_volume", source="Main mic", volume="0.5")
        self.assertEqual(await actions.run("obs.get_volume", source="Main mic"), 0.8)
        self.assertEqual(fake.calls[:3], [
            ("GetSceneItemId", {"sceneName": "desktop", "sourceName": "ghost_vtube_model"}),
            ("SetSceneItemEnabled", {"sceneName": "desktop", "sceneItemId": 7, "sceneItemEnabled": False}),
            ("SetInputVolume", {"inputName": "Main mic", "inputVolumeMul": 0.5})])
        options = actions.get("obs.set_source_visible").options
        self.assertEqual(await options["scene"](), ["desktop", "Just_chatting"])
        self.assertEqual(await options["source"](), ["ghost_vtube_model", "vtube_model"])
        self.assertEqual(await actions.get("obs.set_volume").options["source"](), ["Desktop Audio", "Main mic"])


if __name__ == "__main__":
    unittest.main()
