import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.widgets.widget import Widget
from streamer_toolbox.core.widgets.widget_store import WidgetStore
from streamer_toolbox.gui.services.widget_import_target import WidgetImportTarget


class TestWidgetImportTarget(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.store = WidgetStore(Path(self._dir.name))
        self.target = WidgetImportTarget(self.store)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_a_taken_name_gets_a_number_and_the_files_go_to_its_media_folder(self) -> None:
        self.assertEqual(self.target.add_widget(Widget("chat", "<p>1</p>")), "chat")
        self.assertEqual(self.target.add_widget(Widget("chat", "<p>2</p>"), {"logo.png": b"png"}), "chat_2")
        self.assertEqual(self.target.add_widget(Widget("chat", "<p>3</p>")), "chat_3")
        self.assertEqual(self.target.widget_names(), ["chat", "chat_2", "chat_3"])
        self.assertEqual(self.store.get("chat_2").html, "<p>2</p>")
        self.assertEqual(self.store.media_file("chat_2", "logo.png").read_bytes(), b"png")
