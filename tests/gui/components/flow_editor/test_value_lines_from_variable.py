import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.data.box_value import understand
from streamer_toolbox.core.variables.variable_store import VariableStore
from streamer_toolbox.gui.components.flow_editor.value_lines_input import ValueLinesInput


class TestValueLinesFromVariable(unittest.TestCase):
    """His round 60: a Value line can take a variable's value as it is now (a copy, not the live variable)."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.variables = VariableStore(Path(self._dir.name) / "variables")
        self.changes = []
        self.lines = ValueLinesInput({"model_pos": "1"}, lambda lines, moved: self.changes.append((lines, moved)),
                                     variables=self.variables)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_an_object_becomes_json_text_that_reads_back_as_the_same_object(self) -> None:
        position = {"x": -0.2, "y": 0.1, "model": "Dragon"}
        self.variables.set("model_pos", position)
        self.lines.add_variable("model_pos")
        lines, moved = self.changes[-1]
        self.assertEqual(list(lines), ["model_pos", "model_pos_2"])  # the name was taken
        self.assertEqual(understand(lines["model_pos_2"]), position)
        self.assertEqual(moved, ("", ""))  # a new dot: the canvas is drawn again

    def test_text_stays_as_it_is(self) -> None:
        self.variables.set("greeting", "hello")
        self.lines.add_variable("greeting")
        self.assertEqual(self.changes[-1][0]["greeting"], "hello")


if __name__ == "__main__":
    unittest.main()
