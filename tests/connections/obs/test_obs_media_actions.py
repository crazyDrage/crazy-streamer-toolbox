import unittest

from streamer_toolbox.connections.obs.obs_source_actions import ObsSourceActions
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from tests.fakes.fake_connectable_obs_client import FakeConnectableObsClient

RESPONSES = {
    "GetSceneItemId": {"sceneItemId": 7},
    "GetInputList": {"inputs": [{"inputName": "sound_alert", "inputKind": "ffmpeg_source"},
                                {"inputName": "Main mic", "inputKind": "wasapi_input_capture"},
                                {"inputName": "raid_video_clip", "inputKind": "vlc_source"},
                                {"inputName": "meme_sound_board_image", "inputKind": "image_source"}]},
}


class TestObsMediaActions(unittest.IsolatedAsyncioTestCase):
    """The Media Source boxes: file, size, restart / play / pause / stop."""

    async def test_file_size_and_control(self) -> None:
        fake = FakeConnectableObsClient(responses=RESPONSES)
        actions = ActionRegistry()
        ObsSourceActions(fake.call).add_to(actions)
        await actions.run("obs.set_media_file", source="sound_alert", path="C:/clips/boom.mp4")
        size = await actions.run("obs.set_source_size", scene="desktop", source="sound_alert", width=1280,
                                 height="720", scale="0.5")
        await actions.run("obs.media_control", source="sound_alert", action="restart")
        self.assertEqual(size, {"width": 640.0, "height": 360.0})
        self.assertEqual(fake.calls, [
            ("SetInputSettings", {"inputName": "sound_alert",
                                  "inputSettings": {"local_file": "C:/clips/boom.mp4", "is_local_file": True}}),
            ("GetSceneItemId", {"sceneName": "desktop", "sourceName": "sound_alert"}),
            ("SetSceneItemTransform", {"sceneName": "desktop", "sceneItemId": 7, "sceneItemTransform": {
                "boundsType": "OBS_BOUNDS_SCALE_INNER", "boundsAlignment": 0,
                "boundsWidth": 640.0, "boundsHeight": 360.0}}),
            ("TriggerMediaInputAction", {"inputName": "sound_alert",
                                         "mediaAction": "OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART"})])
        self.assertEqual(await actions.get("obs.set_media_file").options["source"](),
                         ["raid_video_clip", "sound_alert"])  # only media sources

    async def test_image_file(self) -> None:
        fake = FakeConnectableObsClient(responses=RESPONSES)
        actions = ActionRegistry()
        ObsSourceActions(fake.call).add_to(actions)
        await actions.run("obs.set_image_file", source="meme_sound_board_image", path="C:/memes/lizard.png")
        self.assertEqual(fake.calls, [("SetInputSettings", {"inputName": "meme_sound_board_image",
                                                            "inputSettings": {"file": "C:/memes/lizard.png"}})])
        self.assertEqual(await actions.get("obs.set_image_file").options["source"](), ["meme_sound_board_image"])

    async def test_bad_values_fail_before_touching_obs(self) -> None:
        fake = FakeConnectableObsClient(responses=RESPONSES)
        actions = ActionRegistry()
        ObsSourceActions(fake.call).add_to(actions)
        with self.assertRaisesRegex(ValueError, "unknown media action"):
            await actions.run("obs.media_control", source="sound_alert", action="rewind")
        with self.assertRaisesRegex(ValueError, "above 0"):
            await actions.run("obs.set_source_size", scene="desktop", source="sound_alert", width=0, height=720)
        self.assertEqual(fake.calls, [])

    async def test_size_kept_inside_the_canvas(self) -> None:
        responses = dict(RESPONSES, GetVideoSettings={"baseWidth": 1920, "baseHeight": 1080},
                         GetSceneItemTransform={"sceneItemTransform": {"positionX": 1600.0, "positionY": 500.0,
                                                                       "alignment": 5}})
        fake = FakeConnectableObsClient(responses=responses)
        actions = ActionRegistry()
        ObsSourceActions(fake.call).add_to(actions)
        await actions.run("obs.set_source_size", scene="desktop", source="sound_alert", width=300, height=900,
                          keep_inside="true")
        transform = fake.calls[-1][1]["sceneItemTransform"]
        self.assertEqual((transform["positionX"], transform["positionY"], transform["boundsHeight"]),
                         (1600.0, 180.0, 900.0))
