import unittest

from streamer_toolbox.connections.obs.obs_new_source_actions import ObsNewSourceActions
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from tests.fakes.fake_obs_script import FakeObsScript

TRANSFORM = {"positionX": 513.0, "positionY": 0.0, "rotation": 0.0, "scaleX": 0.5, "scaleY": 0.5, "alignment": 5,
             "cropLeft": 0, "cropRight": 0, "cropTop": 0, "cropBottom": 0, "cropToBounds": False,
             "boundsType": "OBS_BOUNDS_NONE", "boundsWidth": 0.0, "boundsHeight": 0.0, "boundsAlignment": 0,
             "sourceWidth": 1920.0, "sourceHeight": 1080.0, "width": 960.0, "height": 540.0}


class TestObsCopySource(unittest.TestCase):
    """His round 82: a copy with its settings, audio, filters and place."""

    def _obs(self, **more) -> FakeObsScript:
        return FakeObsScript({
            "GetInputSettings": {"inputKind": "ffmpeg_source", "inputSettings": {"input": "https://a/b.mp4"}},
            "GetSceneItemId": {"sceneItemId": 4}, "GetSceneItemEnabled": {"sceneItemEnabled": False},
            "CreateInput": {"sceneItemId": 11}, "GetInputVolume": {"inputVolumeMul": 0.4},
            "GetInputMute": {"inputMuted": False}, "GetInputAudioMonitorType": {"monitorType": "OBS_MONITORING_TYPE_NONE"},
            "GetInputAudioTracks": {"inputAudioTracks": {"1": True, "2": False}},
            "GetInputAudioBalance": {"inputAudioBalance": 0.5}, "GetInputAudioSyncOffset": {"inputAudioSyncOffset": 0},
            "GetSourceFilterList": {"filters": [
                {"filterName": "Chroma", "filterKind": "chroma_key_filter_v2", "filterSettings": {"similarity": 400},
                 "filterEnabled": False}]},
            "GetSceneItemTransform": {"sceneItemTransform": TRANSFORM},
            "GetSceneItemBlendMode": {"sceneItemBlendMode": "OBS_BLEND_ADDITIVE"},
            "GetSceneItemLocked": {"sceneItemLocked": True}, "GetSceneItemIndex": {"sceneItemIndex": 2}, **more})

    def _run(self, obs: FakeObsScript, **params):
        import asyncio
        actions = ActionRegistry()
        ObsNewSourceActions(ObsRequests(obs.call)).add_to(actions)
        return asyncio.run(actions.run("obs.copy_source", **params))

    def test_everything_is_copied(self) -> None:
        obs = self._obs()
        made = self._run(obs, scene="Just_chatting", source="so-event", name="so-event 2")
        self.assertEqual(made, {"source": "so-event 2", "scene": "Just_chatting", "item_id": 11})
        self.assertEqual(obs.sent("CreateInput"), [{"sceneName": "Just_chatting", "inputName": "so-event 2",
                                                    "inputKind": "ffmpeg_source",
                                                    "inputSettings": {"input": "https://a/b.mp4"},
                                                    "sceneItemEnabled": False}])
        self.assertEqual(obs.sent("SetInputVolume"), [{"inputName": "so-event 2", "inputVolumeMul": 0.4}])
        self.assertEqual(obs.sent("SetInputAudioTracks"), [{"inputName": "so-event 2",
                                                            "inputAudioTracks": {"1": True, "2": False}}])
        self.assertEqual(obs.sent("CreateSourceFilter")[0]["filterSettings"], {"similarity": 400})
        self.assertEqual(obs.sent("SetSourceFilterEnabled"), [{"sourceName": "so-event 2", "filterName": "Chroma",
                                                               "filterEnabled": False}])
        place = obs.sent("SetSceneItemTransform")[0]["sceneItemTransform"]
        self.assertEqual(place["positionX"], 513.0)
        self.assertNotIn("boundsWidth", place)  # bounds of 0 would be refused
        self.assertNotIn("width", place)
        self.assertEqual(obs.sent("SetSceneItemBlendMode")[0]["sceneItemBlendMode"], "OBS_BLEND_ADDITIVE")
        self.assertEqual(obs.sent("SetSceneItemIndex"), [{"sceneName": "Just_chatting", "sceneItemId": 11,
                                                          "sceneItemIndex": 3}])

    def test_without_sound_into_another_scene(self) -> None:
        obs = self._obs(GetInputVolume=None, GetInputMute=None, GetInputAudioMonitorType=None,
                        GetInputAudioTracks=None, GetInputAudioBalance=None, GetInputAudioSyncOffset=None)
        self._run(obs, scene="Just_chatting", source="logo", name="logo 2", to_scene="Gaming", filters="false")
        self.assertEqual(obs.sent("SetInputVolume"), [])
        self.assertEqual(obs.sent("CreateSourceFilter"), [])
        self.assertEqual(obs.sent("CreateInput")[0]["sceneName"], "Gaming")
        self.assertEqual(obs.sent("SetSceneItemIndex"), [])  # another scene: it goes on top

    def test_a_scene_or_no_name(self) -> None:
        with self.assertRaisesRegex(ValueError, "needs a name"):
            self._run(self._obs(), scene="s", source="so-event", name=" ")
        with self.assertRaisesRegex(ValueError, "can't be copied"):
            self._run(self._obs(GetInputSettings=None), scene="s", source="Gaming", name="x")


if __name__ == "__main__":
    unittest.main()
