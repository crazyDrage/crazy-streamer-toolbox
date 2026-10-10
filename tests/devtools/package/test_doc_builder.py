import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.devtools.package.doc_builder import DocBuilder

FILES = ["llms.txt", "LICENSE", "docs/USER_GUIDE.md", "docs/PLUGINS.md", "docs/ai/rules.md", "docs/ai/use/api.md",
         "docs/ai/notes.txt", "docs/HANDOFF.md", "docs/ARCHITECTURE.md", "config/toolbox.toml", "CLAUDE.md"]


class TestDocBuilder(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.repo = Path(self._dir.name) / "repo"
        self.out = Path(self._dir.name) / "out"
        for path in FILES:
            (self.repo / path).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / path).write_text(path, encoding="utf-8")

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_the_ai_folder_holds_the_index_and_what_it_leads_to_at_the_same_paths(self) -> None:
        builder = DocBuilder(self.repo, self.out)
        self.assertEqual(builder.for_ai_files(), ["llms.txt", "LICENSE", "docs/USER_GUIDE.md", "docs/PLUGINS.md",
                                                  "docs/ai/rules.md", "docs/ai/use/api.md"])
        self.assertEqual(builder._for_ai(self.out), 6)
        self.assertEqual((self.out / "docs" / "ai" / "use" / "api.md").read_text(encoding="utf-8"),
                         "docs/ai/use/api.md")
        self.assertFalse((self.out / "docs" / "HANDOFF.md").exists())  # the developers' notes stay home
        self.assertFalse((self.out / "config").exists())


if __name__ == "__main__":
    unittest.main()

if __name__ == "__main__":
    unittest.main()
