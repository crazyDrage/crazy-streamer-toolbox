import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.variables.variable_store import VariableStore


class TestVariableStore(unittest.TestCase):
    def test_values_survive_a_restart_and_fields_can_be_looked_up(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config" / "variables.json"
            changes = []
            store = VariableStore(path)
            store.on_change(lambda: changes.append(1))
            store.set("spot", {"x": 0.5, "y": -1})
            store.set("count", 3)
            again = VariableStore(path)
            self.assertEqual(again.lookup("spot.x"), 0.5)
            self.assertEqual(again.names(), ["count", "spot"])
            with self.assertRaisesRegex(KeyError, "no field 'z'"):
                again.lookup("spot.z")
            with self.assertRaisesRegex(KeyError, "no variable"):
                again.lookup("nope")
            again.delete("count")
            self.assertEqual(VariableStore(path).names(), ["spot"])
            self.assertEqual(len(changes), 2)

    def test_bad_names_and_values_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = VariableStore(Path(tmp) / "v.json")
            with self.assertRaises(ValueError):
                store.set("with space", 1)
            with self.assertRaises(TypeError):
                store.set("fine", object())


if __name__ == "__main__":
    unittest.main()
