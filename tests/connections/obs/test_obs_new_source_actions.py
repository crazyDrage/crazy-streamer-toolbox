import unittest

from streamer_toolbox.connections.obs.obs_new_source_actions import ObsNewSourceActions
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from tests.fakes.fake_obs_script import FakeObsScript


class TestObsNewSourceActions(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.obs = FakeObsScript({"CreateInput": {"sceneItemId": 9},
                                  "GetInputKindList": {"inputKinds": ["image_source", "my_plugin_source",
                                                                      "browser_source"]}})
        self.actions = ActionRegistry()
        ObsNewSourceActions(ObsRequests(self.obs.call)).add_to(self.actions)

    async def test_create_and_remove(self) -> None:
        made = await self.actions.run("obs.create_source", scene="toolbox_test", name="meme", kind="image_source",
                                      settings='{"file": "C:\\\\meme.png"}', visible="false")
        self.assertEqual(made, {"source": "meme", "scene": "toolbox_test", "item_id": 9})
        self.assertEqual(self.obs.sent("CreateInput"), [{
            "sceneName": "toolbox_test", "inputName": "meme", "inputKind": "image_source",
            "inputSettings": {"file": "C:\\meme.png"}, "sceneItemEnabled": False}])
        await self.actions.run("obs.remove_source", source="meme")
        self.assertEqual(self.obs.sent("RemoveInput"), [{"inputName": "meme"}])

    async def test_bad_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "needs a name"):
            await self.actions.run("obs.create_source", scene="s", name=" ", kind="image_source")
        with self.assertRaisesRegex(ValueError, "settings must be an object"):
            await self.actions.run("obs.create_source", scene="s", name="a", kind="image_source", settings="[1]")

    async def test_kinds_by_obs_menu_name(self) -> None:
        kinds = await self.actions.get("obs.create_source").options["kind"]()
        self.assertEqual(kinds, {"browser_source": "Browser", "image_source": "Image",
                                 "my_plugin_source": "my_plugin_source"})


if __name__ == "__main__":
    unittest.main()
