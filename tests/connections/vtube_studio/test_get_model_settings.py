import unittest

from streamer_toolbox.connections.vtube_studio.vts_look_actions import VtsLookActions
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from tests.fakes.fake_vts_requests import FakeVtsRequests

# shaped like VTube Studio's answers (github.com/DenchiSoft/VTubeStudio)
ANSWERS = {
    "CurrentModelRequest": {"modelLoaded": True, "modelName": "Lizard", "modelID": "abc",
                            "numberOfLive2DParameters": 30, "numberOfLive2DArtmeshes": 80, "hasPhysicsFile": True,
                            "numberOfTextures": 2, "textureResolution": 4096, "timeSinceModelLoaded": 1234,
                            "modelPosition": {"positionX": 0.1, "positionY": 0, "rotation": 0, "size": -50}},
    "HotkeysInCurrentModelRequest": {"availableHotkeys": [
        {"name": "Wave", "type": "TriggerAnimation", "file": "wave.motion3.json", "hotkeyID": "h1",
         "keyCombination": ["LeftControl", "N1"], "onScreenButtonID": 1},
        {"name": "", "type": "ToggleExpression", "file": "smile.exp3.json", "hotkeyID": "h2",
         "keyCombination": [], "onScreenButtonID": -1},
        {"name": "", "type": "RemoveAllExpressions", "file": "", "hotkeyID": "h3", "keyCombination": [],
         "onScreenButtonID": -1}]},
    "ExpressionStateRequest": {"expressions": [
        {"name": "Smile", "file": "smile.exp3.json", "active": False, "deactivateWhenKeyIsLetGo": False,
         "autoDeactivateAfterSeconds": True, "secondsRemaining": 3.2}]},
    "GetCurrentModelPhysicsRequest": {"modelHasPhysics": True, "physicsSwitchedOn": True, "physicsFPSSetting": 60,
                                      "baseStrength": 50, "baseWind": 0, "apiPhysicsOverrideActive": False,
                                      "physicsGroups": [{"groupID": "g1", "groupName": "Hair",
                                                         "strengthMultiplier": 1.2, "windMultiplier": 0.5}]},
}


class TestGetModelSettings(unittest.IsolatedAsyncioTestCase):
    async def test_the_settings_are_one_object_without_what_moves_by_itself(self) -> None:
        vts = FakeVtsRequests(ANSWERS)
        actions = ActionRegistry()
        VtsLookActions(vts).add_to(actions)
        settings = await actions.run("vts.get_model_settings")
        self.assertEqual(settings["model"], "Lizard")
        self.assertEqual((settings["parameters"], settings["parts"], settings["textures"]), (30, 80, 2))
        self.assertEqual(settings["hotkeys"]["Wave"], {"action": "TriggerAnimation", "file": "wave.motion3.json",
                                                       "keys": "LeftControl + N1", "button": 1})
        self.assertEqual(list(settings["hotkeys"]), ["Wave", "(no name)", "(no name) 2"])  # none is lost
        self.assertEqual(settings["expressions"], {"Smile": {"file": "smile.exp3.json", "on": False,
                                                             "off_when_key_let_go": False, "auto_off": True}})
        self.assertEqual(settings["physics"], {"on": True, "fps": 60, "strength": 50, "wind": 0,
                                               "groups": {"Hair": {"strength": 1.2, "wind": 0.5}}})
        text = repr(settings)
        for moving in ("positionX", "1234", "3.2", "apiPhysicsOverrideActive"):
            self.assertNotIn(moving, text)
        self.assertEqual(vts.sent("ExpressionStateRequest"), [{"details": False}])
        self.assertEqual(set(actions.get("vts.get_model_settings").outputs) - set(settings), set())


if __name__ == "__main__":
    unittest.main()
