import asyncio
import unittest
from unittest import mock

from streamer_toolbox.connections.vtube_studio import vts_look_actions
from streamer_toolbox.connections.vtube_studio.vts_look_actions import VtsLookActions, rgba
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from tests.fakes.fake_vts_requests import FakeVtsRequests

EFFECTS = {"postProcessingActive": False, "postProcessingPresets": ["glow", "night"], "postProcessingEffects": [
    {"enumID": "Bloom", "explanation": "Bloom", "configEntries": [
        {"enumID": "Bloom_Strength", "explanation": "Effect on/off"}, {"enumID": "Bloom_StreakColorTint"}]}]}


class TestVtsLookActions(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.vts = FakeVtsRequests({
            "ColorTintRequest": {"matchedArtMeshes": 4},
            "ArtMeshListRequest": {"artMeshNames": ["hair front", "ArtMesh12", "ArtMesh2", "ArtMesh1"]},
            "PostProcessingListRequest": EFFECTS,
            "InputParameterListRequest": {"defaultParameters": [{"name": "MouthOpen"}],
                                          "customParameters": [{"name": "TailWag"}]},
            "ParameterValueRequest": {"name": "MouthOpen", "value": 0.3, "min": 0, "max": 1},
            "FaceFoundRequest": {"found": True},
            "StatisticsRequest": {"framerate": 60, "vTubeStudioVersion": "1.31", "uptime": 3_600_000,
                                  "connectedPlugins": 3}}, clock=lambda: asyncio.get_running_loop().time())
        self.actions = ActionRegistry()
        VtsLookActions(self.vts).add_to(self.actions)

    async def run_box(self, name: str, **params):
        return await self.actions.run(f"vts.{name}", **params)

    async def test_picked_parts_are_tinted_by_their_exact_name(self) -> None:
        await self.run_box("tint", color="blue", picked="ArtMesh1, hair front")
        await self.run_box("reset_tint", parts="tail", picked="ArtMesh1")
        tint, reset = self.vts.sent("ColorTintRequest")
        self.assertEqual(tint["artMeshMatcher"], {"tintAll": False, "nameExact": ["ArtMesh1", "hair front"]})
        self.assertEqual(reset["artMeshMatcher"], {"tintAll": False, "nameContains": ["tail"],
                                                   "nameExact": ["ArtMesh1"]})
        tint_box = self.actions.get("vts.tint")
        self.assertEqual((tint_box.colors, list(tint_box.many)), (("color",), ["picked"]))
        self.assertEqual(await tint_box.many["picked"](), ["ArtMesh1", "ArtMesh2", "ArtMesh12", "hair front"])

    async def test_the_part_under_the_mouse_lights_up_and_the_one_before_goes_back(self) -> None:
        light = self.actions.get("vts.tint").lights["picked"]
        await light("ArtMesh1", "#00FF00")
        await light("ArtMesh1", "#00FF00")  # still on it: lit again, nothing to take away
        await light("hair front", "#00FF00")
        await light("", "#00FF00")
        await light("", "#00FF00")
        sent = [(t["artMeshMatcher"]["nameExact"], t["colorTint"]["colorR"], t["colorTint"]["colorG"])
                for t in self.vts.sent("ColorTintRequest")]
        self.assertEqual(sent, [(["ArtMesh1"], 0, 255), (["ArtMesh1"], 0, 255), (["ArtMesh1"], 255, 255),
                                (["hair front"], 0, 255), (["hair front"], 255, 255)])

    async def test_tint_parts_and_reset(self) -> None:
        self.assertEqual(await self.run_box("tint", color="#FF880080", parts="hair, tail"), {"parts_tinted": 4})
        await self.run_box("reset_tint")
        tint, reset = self.vts.sent("ColorTintRequest")
        self.assertEqual(tint["colorTint"], {"colorR": 255, "colorG": 136, "colorB": 0, "colorA": 128,
                                             "mixWithSceneLightingColor": 1.0})
        self.assertEqual(tint["artMeshMatcher"], {"tintAll": False, "nameContains": ["hair", "tail"]})
        self.assertEqual(reset["artMeshMatcher"], {"tintAll": True})
        self.assertEqual((reset["colorTint"]["colorR"], reset["colorTint"]["colorA"]), (255, 255))

    def test_colours(self) -> None:
        self.assertEqual(rgba("Red"), (255, 48, 48, 255))
        self.assertEqual(rgba("00ff00"), (0, 255, 0, 255))
        with self.assertRaisesRegex(ValueError, "a colour is a name"):
            rgba("bluish")

    async def test_physics_is_sent_again_until_the_time_is_over(self) -> None:
        loop = asyncio.get_running_loop()
        start = loop.time()
        with mock.patch.object(vts_look_actions, "PHYSICS_REPEAT", 0.1):
            await self.run_box("physics", wind="150", seconds=0.25)
        self.assertGreaterEqual(loop.time() - start, 0.25)
        sent = self.vts.sent("SetCurrentModelPhysicsRequest")
        self.assertGreaterEqual(len(sent), 2)
        self.assertEqual(list(sent[0]), ["windOverrides"])  # strength left empty: not touched
        self.assertEqual(sent[0]["windOverrides"][0], {"id": "", "value": 100, "setBaseValue": True,
                                                       "overrideSeconds": 0.5})
        with self.assertRaisesRegex(ValueError, "set strength or wind"):
            await self.run_box("physics")

    async def test_hold_parameter(self) -> None:
        with mock.patch.object(vts_look_actions, "PARAMETER_REPEAT", 0.05):
            await self.run_box("hold_parameter", parameter="MouthOpen", value="1", seconds=0.12, weight=2)
        sent = self.vts.sent("InjectParameterDataRequest")
        self.assertGreaterEqual(len(sent), 2)
        self.assertEqual(sent[0]["parameterValues"], [{"id": "MouthOpen", "value": 1.0, "weight": 1.0}])
        self.assertEqual(await self.actions.get("vts.hold_parameter").options["parameter"](),
                         ["MouthOpen", "TailWag"])
        self.assertEqual(await self.run_box("get_parameter", parameter="MouthOpen"),
                         {"value": 0.3, "min": 0, "max": 1})

    async def test_hold_stops_when_the_flow_stops(self) -> None:
        task = asyncio.create_task(self.run_box("hold_parameter", parameter="MouthOpen", value=1, seconds=60))
        await asyncio.sleep(0.01)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(len(self.vts.sent("InjectParameterDataRequest")), 1)

    async def test_effects(self) -> None:
        self.assertEqual(await self.actions.get("vts.effects_preset").options["preset"](), ["glow", "night"])
        self.assertEqual(await self.actions.get("vts.set_effect").options["setting"](), {
            "Bloom": {"Bloom_Strength": "Bloom_Strength · Effect on/off",
                      "Bloom_StreakColorTint": "Bloom_StreakColorTint"}})
        await self.run_box("effects_preset", preset="glow", fade=5)
        await self.run_box("set_effect", setting="Bloom_Strength", value=0.8)
        await self.run_box("set_effect", setting="Bloom_StreakColorTint", value="#220308FF", only_this="true")
        self.assertTrue(await self.run_box("effects_on", state="toggle"))  # it was off
        await self.run_box("random_effects", chaos=3)
        preset, strength, colour, toggle, chaos = self.vts.sent("PostProcessingUpdateRequest")
        self.assertEqual((preset["setPostProcessingPreset"], preset["presetToSet"], preset["postProcessingFadeTime"]),
                         (True, "glow", 2.0))
        self.assertEqual(strength["postProcessingValues"], [{"configID": "Bloom_Strength", "configValue": "0.8"}])
        self.assertFalse(strength["setAllOtherValuesToDefault"])
        self.assertEqual(colour["postProcessingValues"][0]["configValue"], "220308FF")
        self.assertTrue(colour["setAllOtherValuesToDefault"])
        self.assertEqual((toggle["postProcessingOn"], toggle["setPostProcessingValues"]), (True, False))
        self.assertEqual((chaos["randomizeAll"], chaos["randomizeAllChaosLevel"]), (True, 1.0))

    async def test_face_and_stats(self) -> None:
        self.assertTrue(await self.run_box("face_found"))
        self.assertEqual(await self.run_box("get_stats"), {"fps": 60, "version": "1.31", "minutes": 60,
                                                           "plugins": 3})


if __name__ == "__main__":
    unittest.main()
