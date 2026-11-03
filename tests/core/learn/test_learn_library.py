import re
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.events.event_fields import EVENT_FIELDS
from streamer_toolbox.core.flows.flow_pack import FlowPack
from streamer_toolbox.core.learn.learn_library import LearnLibrary

REF = re.compile(r"\$\{box\.(\w+)(?:\.(\w+))?\}")


class TestLearnLibrary(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, name: str, text: str) -> None:
        (self.folder / name).write_text(text, encoding="utf-8")

    def test_pages_by_section_then_order(self) -> None:
        self.write("b.md", '+++\ntitle = "B"\nsection = "Examples"\norder = 1\n+++\nText of B')
        self.write("a.md", '+++\ntitle = "A"\nsection = "First steps"\norder = 5\n+++\nText of A')
        self.write("z.md", '+++\ntitle = "Z"\nsection = "Alpha"\n+++\nZ')
        self.write("c.md", '+++\ntitle = "C"\nsection = "First steps"\norder = 2\n+++\nC')
        library = LearnLibrary([self.folder])
        self.assertEqual([t.id for t in library.topics()], ["c", "a", "b", "z"])
        self.assertEqual(library.sections(), ["First steps", "Examples", "Alpha"])
        self.assertEqual(library.get("b").text, "Text of B")

    def test_an_example_flow_next_to_it(self) -> None:
        self.write("ex.md", "Just text")
        self.write("ex.flows.toml", 'toolbox_flows = 1\nfolder = "Examples"\n')
        topic = LearnLibrary([self.folder]).get("ex")
        self.assertEqual((topic.title, topic.section, topic.flows.name), ("Ex", "More", "ex.flows.toml"))

    def test_more_folders_are_asked_for_at_every_read(self) -> None:
        more: list[Path] = []
        library = LearnLibrary([], lambda: more)
        self.write("p.md", "A plugin's page")
        self.assertEqual(library.topics(), [])
        more.append(self.folder)  # a plugin switched on
        self.assertEqual([t.id for t in library.topics()], ["p"])

    def test_broken_settings_leave_the_page_out(self) -> None:
        self.write("bad.md", "+++\ntitle = \n+++\ntext")
        self.assertEqual(LearnLibrary([self.folder]).topics(), [])

    def test_the_toolboxs_own_pages(self) -> None:
        """Every page reads; every example flow reads, its triggers are known events and the fields its boxes
        take from a Start box are that event's."""
        topics = LearnLibrary().topics()
        self.assertGreaterEqual(len(topics), 5)
        for topic in topics:
            with self.subTest(topic.id):
                self.assertTrue(topic.text)
                if topic.flows is None:
                    continue
                for flow in FlowPack.from_text(topic.flows.read_text(encoding="utf-8")).flows:
                    kinds = {t.id: t.kind for t in flow.triggers}
                    self.assertTrue(set(kinds.values()) <= set(EVENT_FIELDS))
                    for node in flow.nodes:
                        for value in node.params.values():
                            for box, field in REF.findall(str(value)):
                                if box in kinds:
                                    self.assertIn(field, EVENT_FIELDS[kinds[box]], value)
                                else:
                                    self.assertIsNotNone(flow.node(box), value)


if __name__ == "__main__":
    unittest.main()
