import asyncio
import unittest

from streamer_toolbox.connections.obs.obs_media_playback import ObsMediaPlayback
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from tests.fakes.fake_obs_script import FakeObsScript

PLAYING = {"mediaState": "OBS_MEDIA_STATE_PLAYING", "mediaDuration": 4500, "mediaCursor": 100}
ENDED = {"mediaState": "OBS_MEDIA_STATE_ENDED", "mediaDuration": 4500, "mediaCursor": 4500}
OPENING = {"mediaState": "OBS_MEDIA_STATE_OPENING", "mediaDuration": -1}
SOUND_ALERT = {"positionX": 1600.0, "positionY": 50.0, "rotation": 0.0, "alignment": 5, "boundsType":
               "OBS_BOUNDS_NONE", "boundsWidth": 0.0, "boundsHeight": 0.0, "width": 320.0, "height": 180.0,
               "scaleX": 0.25, "sourceWidth": 1280.0, "cropLeft": 0}


class TestObsMediaPlayback(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.obs = FakeObsScript({"CreateInput": {"sceneItemId": 12, "inputUuid": "u"},
                                  "GetSceneItemId": {"sceneItemId": 3},
                                  "GetSceneItemTransform": {"sceneItemTransform": SOUND_ALERT},
                                  "GetMediaInputStatus": [OPENING, PLAYING, PLAYING, ENDED]})
        self.actions = ActionRegistry()
        ObsMediaPlayback(ObsRequests(self.obs.call), poll_seconds=0, start_timeout=0.5).add_to(self.actions)

    async def test_plays_with_its_own_sound_settings_then_removes_the_source(self) -> None:
        result = await self.actions.run("obs.play_video_once", scene="toolbox_test", file="C:\\clips\\boom.mp4",
                                        tracks="1, 2", volume="0.5", place_like="sound_alert")
        name = result["source"]
        self.assertTrue(name.startswith("toolbox boom "))
        self.assertEqual(result["seconds"], 4.5)
        created = self.obs.sent("CreateInput")[0]
        self.assertEqual((created["sceneName"], created["inputKind"], created["sceneItemEnabled"]),
                         ("toolbox_test", "ffmpeg_source", False))  # hidden until it is set up
        self.assertEqual(created["inputSettings"]["local_file"], "C:\\clips\\boom.mp4")
        self.assertEqual(self.obs.sent("SetInputAudioMonitorType"), [
            {"inputName": name, "monitorType": "OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT"}])
        self.assertEqual(self.obs.sent("SetInputAudioTracks")[0]["inputAudioTracks"],
                         {"1": True, "2": True, "3": False, "4": False, "5": False, "6": False})
        self.assertEqual(self.obs.sent("SetInputVolume"), [{"inputName": name, "inputVolumeMul": 0.5}])
        place = self.obs.sent("SetSceneItemTransform")[0]
        self.assertEqual(place["sceneItemId"], 12)
        self.assertEqual(place["sceneItemTransform"], {
            "positionX": 1600.0, "positionY": 50.0, "rotation": 0.0, "alignment": 5, "cropLeft": 0,
            "boundsType": "OBS_BOUNDS_SCALE_INNER", "boundsWidth": 320.0, "boundsHeight": 180.0})
        kinds = self.obs.kinds()
        self.assertLess(kinds.index("SetSceneItemTransform"), kinds.index("SetSceneItemEnabled"))
        self.assertEqual(kinds[-1], "RemoveInput")
        self.assertEqual(self.obs.sent("RemoveInput"), [{"inputName": name}])

    async def test_a_place_of_its_own_wins_over_place_like(self) -> None:
        await self.actions.run("obs.play_video_once", scene="s", file="C:\\a.mp4", place_like="sound_alert",
                               place={"x": 100, "y": 50, "width": 320, "height": 180})
        self.assertEqual(self.obs.sent("SetSceneItemTransform"), [{"sceneName": "s", "sceneItemId": 12, "sceneItemTransform": {
            "positionX": 100.0, "positionY": 50.0, "rotation": 0.0, "alignment": 5,
            "boundsType": "OBS_BOUNDS_SCALE_INNER", "boundsAlignment": 0, "boundsWidth": 320.0,
            "boundsHeight": 180.0}}])
        self.assertNotIn("GetSceneItemTransform", self.obs.kinds())

    async def test_a_clip_shorter_than_one_look_still_ends(self) -> None:
        self.obs.responses["GetMediaInputStatus"] = [OPENING, ENDED]
        await self.actions.run("obs.play_video_once", scene="s", file="C:\\a.mp4")
        self.assertEqual(self.obs.kinds()[-1], "RemoveInput")
        self.assertEqual(self.obs.sent("SetInputAudioTracks"), [])  # empty tracks: OBS's default stays

    async def test_a_video_that_never_starts_is_removed_with_an_error(self) -> None:
        self.obs.responses["GetMediaInputStatus"] = [OPENING]
        with self.assertRaisesRegex(TimeoutError, "didn't start"):
            await self.actions.run("obs.play_video_once", scene="s", file="C:\\a.mp4")
        self.assertEqual(self.obs.kinds()[-1], "RemoveInput")

    async def test_a_failed_set_up_removes_the_new_source(self) -> None:
        self.obs.responses["GetSceneItemId"] = None  # place_like names a source that isn't in the scene
        with self.assertRaisesRegex(Exception, "GetSceneItemId failed"):
            await self.actions.run("obs.play_video_once", scene="s", file="C:\\a.mp4", place_like="gone")
        self.assertEqual(self.obs.kinds()[-1], "RemoveInput")
        self.assertNotIn("SetSceneItemEnabled", self.obs.kinds())

    async def test_without_waiting_it_still_goes_when_over(self) -> None:
        result = await self.actions.run("obs.play_video_once", scene="s", file="C:\\a.mp4", wait="false")
        self.assertNotIn("RemoveInput", self.obs.kinds())
        for _ in range(20):
            await asyncio.sleep(0)
        self.assertEqual(self.obs.sent("RemoveInput"), [{"inputName": result["source"]}])

    async def test_stopping_the_flow_removes_it_too(self) -> None:
        self.obs.responses["GetMediaInputStatus"] = [PLAYING]
        task = asyncio.create_task(self.actions.run("obs.play_video_once", scene="s", file="C:\\a.mp4"))
        for _ in range(10):
            await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(self.obs.kinds()[-1], "RemoveInput")

    async def test_the_same_in_parts(self) -> None:
        made = await self.actions.run("obs.new_media_source", scene="toolbox_test", file="C:\\clips\\boom.mp4")
        self.assertTrue(made["source"].startswith("toolbox boom "))
        self.assertEqual((made["scene"], made["item_id"]), ("toolbox_test", 12))
        self.assertFalse(self.obs.sent("CreateInput")[0]["sceneItemEnabled"])
        self.obs.responses["GetSceneItemId"] = [{"sceneItemId": 12}, {"sceneItemId": 3}]
        await self.actions.run("obs.place_like", scene="toolbox_test", source=made["source"], like="sound_alert")
        place = self.obs.sent("SetSceneItemTransform")[0]
        self.assertEqual((place["sceneItemId"], place["sceneItemTransform"]["positionX"]), (12, 1600.0))
        self.assertEqual(self.obs.sent("GetSceneItemTransform"), [{"sceneName": "toolbox_test", "sceneItemId": 3}])
        over = await self.actions.run("obs.wait_media_end", source=made["source"])
        self.assertEqual(over, {"seconds": 4.5})
        self.assertNotIn("RemoveInput", self.obs.kinds())  # removing is its own box (Remove source)

    async def test_a_new_media_source_can_have_its_own_name(self) -> None:
        made = await self.actions.run("obs.new_media_source", scene="s", file="C:\\a.mp4", name="my clip",
                                      visible="true")
        self.assertEqual(made["source"], "my clip")
        self.assertTrue(self.obs.sent("CreateInput")[0]["sceneItemEnabled"])
        with self.assertRaisesRegex(ValueError, "which file"):
            await self.actions.run("obs.new_media_source", scene="s", file=" ")

    async def test_media_status(self) -> None:
        self.obs.responses["GetMediaInputStatus"] = PLAYING
        status = await self.actions.run("obs.get_media_status", source="sound_alert")
        self.assertEqual(status, {"state": "playing", "seconds": 4.5, "position": 0.1})


if __name__ == "__main__":
    unittest.main()
