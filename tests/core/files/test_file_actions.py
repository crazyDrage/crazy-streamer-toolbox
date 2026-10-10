import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.files.file_actions import FileActions


class TestFileActions(unittest.IsolatedAsyncioTestCase):
    async def test_write_append_read_and_hidden_from_the_api(self) -> None:
        actions = ActionRegistry()
        FileActions().add_to(actions)
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "counters" / "lizard_combo.txt")
            await actions.run("file.write_text", path=path, text=12)
            self.assertEqual(await actions.run("file.read_text", path=path), "12")
            await actions.run("file.write_text", path=path, text="13", append=True)
            self.assertEqual(Path(path).read_text(encoding="utf-8"), "12\n13\n")  # a line of its own
            await actions.run("file.write_text", path=path, text="14", append="true")
            self.assertEqual(await actions.run("file.read_text", path=path), "12\n13\n14")
            await actions.run("file.write_text", path=path, text="15", append="false")  # a hand-written flow
            self.assertEqual(await actions.run("file.read_text", path=path), "15")
            new = str(Path(tmp) / "new.txt")
            await actions.run("file.write_text", path=new, text="first", append=True)
            self.assertEqual(Path(new).read_text(encoding="utf-8"), "first\n")
        self.assertEqual([a.name for a in actions.all()], [])


if __name__ == "__main__":
    unittest.main()
