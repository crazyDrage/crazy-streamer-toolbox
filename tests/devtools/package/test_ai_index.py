import unittest
from pathlib import Path


class TestAiIndex(unittest.TestCase):
    """llms.txt is the index of the docs for AI agents: a file without a row there is never read."""

    REPO = Path(__file__).resolve().parents[3]

    def test_every_ai_doc_has_a_row_and_every_row_has_its_file(self) -> None:
        index = (self.REPO / "llms.txt").read_text(encoding="utf-8")
        for file in sorted((self.REPO / "docs" / "ai").rglob("*.md")):
            self.assertIn(file.relative_to(self.REPO).as_posix(), index)
        for word in index.replace("(", " ").replace(")", " ").replace("`", " ").replace(",", " ").split():
            if word.startswith("docs/") and word.endswith(".md"):
                self.assertTrue((self.REPO / word).is_file(), word)

if __name__ == "__main__":
    unittest.main()
