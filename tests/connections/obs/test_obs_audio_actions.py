import unittest

from streamer_toolbox.connections.obs.obs_audio_actions import ObsAudioActions, track_numbers
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from tests.fakes.fake_obs_script import FakeObsScript


class TestObsAudioActions(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.obs = FakeObsScript({
            "GetInputAudioMonitorType": {"monitorType": "OBS_MONITORING_TYPE_MONITOR_ONLY"},
            "GetInputAudioTracks": {"inputAudioTracks": {"1": True, "2": False, "3": True, "4": False,
                                                         "5": False, "6": False}},
            "ToggleInputMute": {"inputMuted": True}, "GetInputMute": {"inputMuted": False}})
        self.actions = ActionRegistry()
        ObsAudioActions(ObsRequests(self.obs.call)).add_to(self.actions)

    async def test_monitoring_by_its_mixer_name(self) -> None:
        await self.actions.run("obs.set_audio_monitoring", source="sound_alert", monitoring="Monitor and output")
        self.assertEqual(self.obs.sent("SetInputAudioMonitorType"), [
            {"inputName": "sound_alert", "monitorType": "OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT"}])
        self.assertEqual(await self.actions.run("obs.get_audio_monitoring", source="sound_alert"), "monitor only")
        with self.assertRaisesRegex(ValueError, "monitoring is one of off"):
            await self.actions.run("obs.set_audio_monitoring", source="x", monitoring="loud")

    async def test_tracks(self) -> None:
        self.assertEqual(await self.actions.run("obs.set_audio_tracks", source="mic", tracks="2,1"), [1, 2])
        self.assertEqual(self.obs.sent("SetInputAudioTracks")[0]["inputAudioTracks"],
                         {"1": True, "2": True, "3": False, "4": False, "5": False, "6": False})
        self.assertEqual(await self.actions.run("obs.get_audio_tracks", source="mic"), [1, 3])

    def test_track_numbers(self) -> None:
        self.assertEqual(track_numbers("1 3"), ["1", "3"])
        self.assertEqual(track_numbers("[2, 1]"), ["1", "2"])
        self.assertEqual(track_numbers([6]), ["6"])
        self.assertEqual(track_numbers(4), ["4"])
        self.assertEqual(track_numbers("all"), ["1", "2", "3", "4", "5", "6"])
        self.assertEqual(track_numbers("none"), [])
        with self.assertRaisesRegex(ValueError, "1 to 6, not 7"):
            track_numbers("7")
        with self.assertRaisesRegex(ValueError, "numbers 1 to 6"):
            track_numbers("one")

    async def test_mute(self) -> None:
        self.assertTrue(await self.actions.run("obs.set_mute", source="mic", mute="toggle"))
        self.assertFalse(await self.actions.run("obs.set_mute", source="mic", mute="unmute"))
        self.assertTrue(await self.actions.run("obs.set_mute", source="mic"))
        self.assertEqual(self.obs.sent("SetInputMute"), [{"inputName": "mic", "inputMuted": False},
                                                         {"inputName": "mic", "inputMuted": True}])
        self.assertFalse(await self.actions.run("obs.get_mute", source="mic"))


if __name__ == "__main__":
    unittest.main()
