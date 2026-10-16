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

    def test_every_variable_is_its_own_file_and_a_delete_removes_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "variables"
            store = VariableStore(folder)
            store.set("count", 3)
            store.set("spot", {"x": 0.5})
            store.set("count", 4)
            self.assertEqual(["count.json", "spot.json"], sorted(file.name for file in folder.iterdir()))
            self.assertEqual("4", (folder / "count.json").read_text(encoding="utf-8"))
            store.delete("count")
            self.assertEqual(["spot.json"], [file.name for file in folder.iterdir()])

    def test_a_name_that_differs_only_in_case_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = VariableStore(Path(tmp) / "variables")
            store.set("count", 1)
            with self.assertRaisesRegex(ValueError, "already a variable 'count'"):
                store.set("Count", 2)
            store.set("count", 2)
            self.assertEqual({"count": 2}, store.all())

    def test_the_one_file_of_before_is_taken_apart_once_and_kept(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old = Path(tmp) / "variables.json"
            old.write_text('{"count": 3, "spot": {"x": 0.5}, "Count": 9}', encoding="utf-8")
            with self.assertLogs("streamer_toolbox.core.variables.variable_store", "WARNING"):
                store = VariableStore(Path(tmp) / "variables", old)
            self.assertEqual({"count": 3, "spot": {"x": 0.5}}, store.all())
            self.assertFalse(old.exists())
            self.assertIn('"Count": 9', (Path(tmp) / "variables.json.old").read_text(encoding="utf-8"))

            store.set("count", 4)
            old.write_text('{"count": 100}', encoding="utf-8")  # a stray old file later changes nothing
            self.assertEqual(4, VariableStore(Path(tmp) / "variables", old).get("count"))

    def test_a_broken_file_does_not_stop_the_others(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "variables"
            VariableStore(folder).set("count", 3)
            (folder / "half.json").write_text("{", encoding="utf-8")
            with self.assertLogs("streamer_toolbox.core.variables.variable_store", "WARNING"):
                self.assertEqual({"count": 3}, VariableStore(folder).all())


if __name__ == "__main__":
    unittest.main()
