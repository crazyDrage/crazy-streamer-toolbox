import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.variables.boxes.delete_variable import DeleteVariable
from streamer_toolbox.core.variables.variable_store import VariableStore


class TestDeleteVariable(unittest.IsolatedAsyncioTestCase):
    async def test_removes_the_variable_and_its_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "variables"
            store = VariableStore(folder)
            store.set("token", "abc")
            store.set("count", 3)
            self.assertTrue(await DeleteVariable(store).run("token"))
            self.assertEqual(["count"], store.names())
            self.assertEqual(["count.json"], [file.name for file in folder.iterdir()])

    async def test_a_missing_variable_is_fine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = VariableStore(Path(tmp) / "variables")
            self.assertFalse(await DeleteVariable(store).run("nope"))
