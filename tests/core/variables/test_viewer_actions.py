import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.variables.variable_store import VariableStore
from streamer_toolbox.core.variables.viewer_actions import ViewerActions


class TestViewerActions(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.variables = VariableStore(Path(self._dir.name) / "variables.json")
        self.viewers = ViewerActions(self.variables)

    def tearDown(self) -> None:
        self._dir.cleanup()

    async def test_counts_per_viewer(self) -> None:
        self.assertEqual(await self.viewers.add("lurks", "VexFan"), 1)
        self.assertEqual(await self.viewers.add("lurks", "vexfan", 2), 3)
        await self.viewers.add("lurks", "Kit")
        await self.viewers.set("lurks", "Quiet", 0)
        self.assertEqual(self.variables.get("lurks"), {"vexfan": 3, "kit": 1, "quiet": 0})
        self.assertEqual(await self.viewers.get("lurks", "KIT"), 1)
        self.assertEqual(await self.viewers.get("lurks", "nobody", default=0), 0)
        self.assertEqual(await self.viewers.top("lurks", 2), [{"user": "vexfan", "value": 3},
                                                              {"user": "kit", "value": 1}])

    async def test_bad_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "no viewer"):
            await self.viewers.add("lurks", "")
        self.variables.set("lizard_timer", 5)
        with self.assertRaisesRegex(ValueError, "isn't a per-viewer variable"):
            await self.viewers.add("lizard_timer", "kit")


if __name__ == "__main__":
    unittest.main()
