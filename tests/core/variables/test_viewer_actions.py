import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.variables.boxes.add_to_viewer_value import AddToViewerValue
from streamer_toolbox.core.variables.boxes.get_viewer_value import GetViewerValue
from streamer_toolbox.core.variables.boxes.set_viewer_value import SetViewerValue
from streamer_toolbox.core.variables.boxes.top_viewers import TopViewers
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
        self.assertEqual(await AddToViewerValue(self.variables).run("lurks", "VexFan"), 1)
        self.assertEqual(await AddToViewerValue(self.variables).run("lurks", "vexfan", 2), 3)
        await AddToViewerValue(self.variables).run("lurks", "Kit")
        await SetViewerValue(self.variables).run("lurks", "Quiet", 0)
        self.assertEqual(self.variables.get("lurks"), {"vexfan": 3, "kit": 1, "quiet": 0})
        self.assertEqual(await GetViewerValue(self.variables).run("lurks", "KIT"), 1)
        self.assertEqual(await GetViewerValue(self.variables).run("lurks", "nobody", default=0), 0)
        self.assertEqual(await TopViewers(self.variables).run("lurks", 2), [{"user": "vexfan", "value": 3},
                                                              {"user": "kit", "value": 1}])

    async def test_bad_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "no viewer"):
            await AddToViewerValue(self.variables).run("lurks", "")
        self.variables.set("lizard_timer", 5)
        with self.assertRaisesRegex(ValueError, "isn't a per-viewer variable"):
            await AddToViewerValue(self.variables).run("lizard_timer", "kit")


if __name__ == "__main__":
    unittest.main()
