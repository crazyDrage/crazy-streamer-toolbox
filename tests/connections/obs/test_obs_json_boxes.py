import json
import unittest

from streamer_toolbox.connections.obs.obs_protocol import ObsProtocol
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.connections.obs_connection import JSON_BOXES
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.json_boxes import JsonBoxes
from streamer_toolbox.core.values.value_kind import ValueKind
from streamer_toolbox.core.values.value_kinds import ValueKinds
from tests.fakes.fake_obs_script import FakeObsScript


class TestObsJsonBoxes(unittest.IsolatedAsyncioTestCase):
    """The OBS boxes that are written as JSON (connections/obs/boxes), against the scripted fake."""

    def setUp(self) -> None:
        self.obs = FakeObsScript({"GetSceneList": {"scenes": [{"sceneName": "desktop"}, {"sceneName": "game"}]}})
        requests = ObsRequests(self.obs.call)
        kinds = ValueKinds([ValueKind(name, name, extra="options", setting=requests.scene_names)
                            for name in ("obs.scene", "obs.source", "obs.scene_item")])
        self.boxes = JsonBoxes(JSON_BOXES, kinds)
        self.actions = ActionRegistry()
        self.boxes.add_to(self.actions, "obs", requests)

    def test_every_box_sends_a_request_obs_has_with_fields_it_knows(self) -> None:
        protocol = ObsProtocol()._requests
        self.assertTrue(self.boxes.boxes)
        for box in self.boxes.boxes:
            with self.subTest(box=box.name):
                self.assertIn(box.request, protocol)
                known = {field["name"] for field in protocol[box.request]["fields"]}
                self.assertLessEqual({field.sent_name for field in box.fields} | set(box.fixed), known)
                needed = {field["name"] for field in protocol[box.request]["fields"] if not field["optional"]}
                self.assertLessEqual(needed, {f.sent_name for f in box.fields if not f.optional} | set(box.fixed))
                self.assertTrue(box.label and box.help and box.group)

    async def test_boxes_send_their_request(self) -> None:
        self.assertEqual(await self.actions.get("obs.set_preview_scene").options["scene"](), ["game", "desktop"])
        await self.actions.run("obs.set_preview_scene", scene="game")
        await self.actions.run("obs.set_studio_mode")
        await self.actions.run("obs.studio_transition")
        await self.actions.run("obs.add_recording_chapter")
        await self.actions.run("obs.open_source_projector", source="camera")
        self.assertEqual(self.obs.sent("SetCurrentPreviewScene"), [{"sceneName": "game"}])
        self.assertEqual(self.obs.sent("SetStudioModeEnabled"), [{"studioModeEnabled": True}])
        self.assertEqual(self.obs.sent("OpenSourceProjector"), [{"sourceName": "camera", "monitorIndex": -1}])
        self.assertEqual(json.dumps(self.obs.sent("CreateRecordChapter")), "[{}]")
        self.assertIn("TriggerStudioModeTransition", self.obs.kinds())


if __name__ == "__main__":
    unittest.main()
