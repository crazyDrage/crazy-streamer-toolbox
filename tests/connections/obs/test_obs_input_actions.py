import unittest

from streamer_toolbox.connections.obs.obs_input_actions import ObsInputActions
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from tests.fakes.fake_connectable_obs_client import FakeConnectableObsClient

RESPONSES = {
    "GetSceneItemId": {"sceneItemId": 7},
    "GetSceneItemTransform": {"sceneItemTransform": {"positionX": 1140.0, "positionY": 632.0}},
    "GetInputSettings": {"inputSettings": {"text": "Tracking On!", "font": {"size": 48}}},
    "GetInputList": {"inputs": [{"inputName": "tracking_text", "inputKind": "text_gdiplus_v3"},
                                {"inputName": "sound_alert", "inputKind": "ffmpeg_source"}]},
}


class TestObsInputActions(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.fake = FakeConnectableObsClient(responses=RESPONSES)
        self.actions = ActionRegistry()
        ObsInputActions(self.fake.call).add_to(self.actions)

    async def test_text_and_settings(self) -> None:
        await self.actions.run("obs.set_text", source="tracking_text", text="Tracking Lost!")
        settings = await self.actions.run("obs.get_source_settings", source="tracking_text")
        await self.actions.run("obs.set_source_settings", source="tracking_text", settings='{"text": "hi"}')
        self.assertEqual(settings["font"], {"size": 48})
        self.assertEqual(self.fake.calls[0], ("SetInputSettings", {"inputName": "tracking_text",
                                                                   "inputSettings": {"text": "Tracking Lost!"}}))
        self.assertEqual(self.fake.calls[-1], ("SetInputSettings", {"inputName": "tracking_text",
                                                                    "inputSettings": {"text": "hi"}, "overlay": True}))
        self.assertEqual(await self.actions.get("obs.set_text").options["source"](), ["tracking_text"])
        with self.assertRaisesRegex(ValueError, "must be an object"):
            await self.actions.run("obs.set_source_settings", source="x", settings="text=hi")

    async def test_settings_take_create_sources_result_but_not_its_item_id(self) -> None:
        await self.actions.run("obs.get_source_settings", source={"source": "meme", "scene": "s", "item_id": 9})
        self.assertEqual(self.fake.calls[-1], ("GetInputSettings", {"inputName": "meme"}))
        with self.assertRaisesRegex(ValueError, "take 'source', not 'item_id'"):
            await self.actions.run("obs.get_source_settings", source=9)

    async def test_move_keeps_an_empty_value(self) -> None:
        place = await self.actions.run("obs.move_source", scene="desktop", source="sound_alert", y="200")
        self.assertEqual(place, {"x": 1140.0, "y": 200.0})
        self.assertEqual(self.fake.calls[-1], ("SetSceneItemTransform", {
            "sceneName": "desktop", "sceneItemId": 7, "sceneItemTransform": {"positionX": 1140.0,
                                                                             "positionY": 200.0}}))


if __name__ == "__main__":
    unittest.main()
