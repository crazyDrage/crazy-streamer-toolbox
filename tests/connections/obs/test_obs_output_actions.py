import unittest

from streamer_toolbox.connections.obs.obs_output_actions import ObsOutputActions
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from tests.fakes.fake_obs_script import FakeObsScript


class TestObsOutputActions(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.obs = FakeObsScript({
            "StopRecord": {"outputPath": "C:\\rec\\a.mkv"},
            "GetStreamStatus": {"outputActive": True, "outputDuration": 61_400},
            "GetRecordStatus": {"outputActive": False, "outputDuration": 0},
            "GetStats": {"cpuUsage": 3.14159, "memoryUsage": 812.6, "activeFps": 60.0000001,
                         "renderSkippedFrames": 2, "outputSkippedFrames": 0},
            "GetHotkeyList": {"hotkeys": ["OBSBasic.StartRecording", "libobs.mute"]},
            "GetSceneList": {"scenes": [{"sceneName": "desktop"}, {"sceneName": "toolbox_test"}]},
            "GetSceneItemList": {"sceneItems": [{"sourceName": "sound_alert"}]}})
        self.actions = ActionRegistry()
        ObsOutputActions(ObsRequests(self.obs.call)).add_to(self.actions)

    async def test_record_stream_replay_camera(self) -> None:
        self.assertEqual(await self.actions.run("obs.record", action="stop"), "C:\\rec\\a.mkv")
        await self.actions.run("obs.stream", action="start")
        await self.actions.run("obs.replay_buffer")
        await self.actions.run("obs.virtual_camera", action="stop")
        self.assertEqual(self.obs.kinds(), ["StopRecord", "StartStream", "SaveReplayBuffer", "StopVirtualCam"])
        with self.assertRaisesRegex(ValueError, "action is one of start, stop, toggle"):
            await self.actions.run("obs.stream", action="pause")

    async def test_status_and_stats(self) -> None:
        self.assertEqual(await self.actions.run("obs.get_output_status"), {
            "streaming": True, "recording": False, "stream_seconds": 61, "record_seconds": 0})
        self.assertEqual(await self.actions.run("obs.get_stats"), {
            "cpu": 3.1, "memory_mb": 813, "fps": 60.0, "render_skipped": 2, "output_skipped": 0})

    async def test_screenshot(self) -> None:
        path = await self.actions.run("obs.screenshot", source="desktop", file="C:\\shots\\now.JPG", width="640")
        self.assertEqual(path, "C:\\shots\\now.JPG")
        self.assertEqual(self.obs.sent("SaveSourceScreenshot"), [
            {"sourceName": "desktop", "imageFormat": "jpg", "imageFilePath": "C:\\shots\\now.JPG", "imageWidth": 640}])
        with self.assertRaisesRegex(ValueError, "should end in"):
            await self.actions.run("obs.screenshot", source="desktop", file="C:\\shots\\now.gif")
        with self.assertRaisesRegex(ValueError, "full path"):
            await self.actions.run("obs.screenshot", source="desktop", file="now.png")
        names = await self.actions.get("obs.screenshot").options["source"]()
        self.assertEqual(names, ["toolbox_test", "desktop", "sound_alert"])

    async def test_hotkeys(self) -> None:
        self.assertEqual(await self.actions.get("obs.trigger_hotkey").options["hotkey"](),
                         ["libobs.mute", "OBSBasic.StartRecording"])
        await self.actions.run("obs.trigger_hotkey", hotkey="libobs.mute")
        self.assertEqual(self.obs.sent("TriggerHotkeyByName"), [{"hotkeyName": "libobs.mute"}])


if __name__ == "__main__":
    unittest.main()
