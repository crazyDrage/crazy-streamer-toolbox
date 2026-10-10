import inspect
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.json_boxes import JsonBoxes
from streamer_toolbox.core.files.file_types import IMAGE_TYPES
from streamer_toolbox.core.values.value_kind import ValueKind
from streamer_toolbox.core.values.value_kinds import ValueKinds

LAMP = {"group": "Light", "boxes": [
    {"name": "set_light", "label": "Set light", "help": "Sets the lamp", "request": "SetLight",
     "fixed": {"lamp": 1},
     "fields": [{"name": "room", "kind": "lamp.room"},
                {"name": "tint", "send_as": "colorHex", "kind": "color", "label": "Colour"},
                {"name": "level", "kind": "number", "default": 50, "hint": "0 to 100"},
                {"name": "mode", "kind": "choice", "choices": ["steady", "blink"], "optional": True},
                {"name": "picture", "kind": "image", "optional": True},
                {"name": "steps", "kind": "list", "optional": True}]},
    {"name": "lights_off", "request": "AllOff", "group": "Other", "flow_only": True}]}


class TestJsonBoxes(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name)
        self.sent: list[tuple[str, dict[str, Any]]] = []
        self.actions = ActionRegistry()

    def tearDown(self) -> None:
        self._dir.cleanup()

    async def _send(self, request: str, data: dict[str, Any]) -> dict[str, Any]:
        self.sent.append((request, data))
        return {"ok": True}

    @staticmethod
    async def _rooms() -> list[str]:
        return ["kitchen", "hall"]

    def _load(self, content: dict[str, Any] = LAMP, name: str = "light.json") -> None:
        (self.folder / name).write_text(json.dumps(content), encoding="utf-8")
        kinds = ValueKinds([ValueKind("lamp.room", "Room", extra="options", setting=self._rooms)])
        JsonBoxes(self.folder, kinds).add_to(self.actions, "lamp", self._send)

    async def test_a_file_becomes_boxes_with_what_their_kinds_ask_for(self) -> None:
        self._load()
        box = self.actions.get("lamp.set_light")
        self.assertEqual((box.title, box.description, box.group, box.flow_only),
                         ("Set light", "Sets the lamp", "Light", False))
        self.assertEqual(box.labels, {"tint": "Colour"})
        self.assertEqual(box.hints, {"level": "0 to 100"})
        self.assertEqual(box.colors, ("tint",))
        self.assertEqual(box.files, {"picture": IMAGE_TYPES})
        self.assertEqual(await box.options["room"](), ["kitchen", "hall"])
        self.assertEqual(await box.options["mode"](), ["steady", "blink"])
        parameters = inspect.signature(box.handler).parameters
        self.assertEqual({name: (p.default, p.annotation) for name, p in parameters.items()}, {
            "room": ("", str), "tint": ("", str), "level": (50, float), "mode": ("", str), "picture": ("", str),
            "steps": ("", str)})
        off = self.actions.get("lamp.lights_off")
        self.assertEqual((off.title, off.group, off.flow_only), ("Lights off", "Other", True))

    async def test_running_a_box_sends_the_request_with_the_programs_names(self) -> None:
        self._load()
        answer = await self.actions.run("lamp.set_light", room="hall", tint="#FF8800", level="20", steps="[1, 2]")
        self.assertEqual(answer, {"ok": True})
        await self.actions.run("lamp.set_light", room="hall", tint="#000000", mode="blink")
        await self.actions.run("lamp.lights_off")
        self.assertEqual(self.sent, [
            ("SetLight", {"lamp": 1, "room": "hall", "colorHex": "#FF8800", "level": 20, "steps": [1, 2]}),
            ("SetLight", {"lamp": 1, "room": "hall", "colorHex": "#000000", "level": 50, "mode": "blink"}),
            ("AllOff", {})])

    async def test_an_empty_needed_field_or_a_value_that_does_not_fit_is_refused(self) -> None:
        self._load()
        with self.assertRaisesRegex(ValueError, "Set light: Colour is empty"):
            await self.actions.run("lamp.set_light", room="hall")
        with self.assertRaisesRegex(ValueError, "Set light, level: 'bright' is not a number"):
            await self.actions.run("lamp.set_light", room="hall", tint="#fff", level="bright")
        self.assertEqual(self.sent, [])

    def test_a_file_that_is_wrong_names_itself(self) -> None:
        for content, message in (
                ({"boxes": [{"name": "x", "request": "X", "fields": [{"name": "a", "kind": "vts.animation"}]}]},
                 "light.json: box 'x', field 'a': unknown value kind 'vts.animation'"),
                ({"boxes": [{"name": "x", "request": "X", "fields": [{"name": "a", "kind": "choice"}]}]},
                 "light.json: box 'x', field 'a': a choice needs"),
                ({"boxes": [{"name": "x"}]}, "light.json: a box needs \"name\" and \"request\""),
                ({"boxes": [{"name": "x", "request": "X", "fields": [{"name": "a"}, {"name": "a"}]}]},
                 "light.json: box 'x' has a field name twice"),
                ({"boxes": [{"name": "x", "request": "X", "fields": [{"name": "a", "typo": 1}]}]},
                 "light.json: a field needs"),
                ({"group": "no boxes"}, "light.json: 'boxes'")):
            with self.subTest(message=message), self.assertRaises(ValueError) as raised:
                self._load(content)
            self.assertIn(message, str(raised.exception))

    def test_every_file_of_the_folder_is_read(self) -> None:
        (self.folder / "more.json").write_text(json.dumps({"boxes": [{"name": "blink", "request": "Blink"}]}),
                                               encoding="utf-8")
        self._load()
        self.assertEqual([a.name for a in self.actions.all(include_flow_only=True)],
                         ["lamp.blink", "lamp.lights_off", "lamp.set_light"])


if __name__ == "__main__":
    unittest.main()
