import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.widgets.widget import Widget, check_name
from streamer_toolbox.core.widgets.widget_store import WidgetStore, parse_fields

FIELDS = {"title": {"type": "text", "label": "Title", "value": "Latest follower"},
          "size": {"type": "slider", "label": "Size", "value": 32, "min": 10, "max": 100},
          "ding": {"type": "sound-input", "label": "Sound"},
          "reset": {"type": "button", "label": "Reset", "value": "now"}}


class TestWidgetStore(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name) / "widgets"
        self.store = WidgetStore(self.folder)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_a_widget_is_four_plain_files_plus_his_values(self) -> None:
        self.assertEqual(self.store.names(), [])
        self.store.save(Widget("follow_box", "<div>{{title}}</div>", "div { color: red }", "let a = 1;", FIELDS,
                               {"size": 48}))
        self.assertEqual(sorted(p.name for p in (self.folder / "follow_box").iterdir()),
                         ["fields.json", "values.json", "widget.css", "widget.html", "widget.js"])
        widget = WidgetStore(self.folder).get("follow_box")
        self.assertEqual((widget.html, widget.css, widget.js), ("<div>{{title}}</div>", "div { color: red }",
                                                                "let a = 1;"))
        self.assertEqual(widget.field_data(), {"title": "Latest follower", "size": 48, "ding": ""})  # no button
        self.assertEqual(widget.media_fields(), ["ding"])
        self.assertEqual(self.store.names(), ["follow_box"])

    def test_the_media_folder_gives_its_own_files_and_nothing_else(self) -> None:
        self.store.save(Widget("scene"))
        self.store.save_media("scene", "ab12.webm", b"video")
        self.assertEqual(self.store.media_file("scene", "ab12.webm").read_bytes(), b"video")
        (self.folder / "scene" / "values.json").write_text("{}", encoding="utf-8")
        for name in ("missing.png", "../values.json", "..", "sub/ab12.webm", ""):
            self.assertIsNone(self.store.media_file("scene", name))
        self.assertIsNone(self.store.media_file("../scene", "ab12.webm"))
        with self.assertRaises(ValueError):
            self.store.save_media("scene", "../out.txt", b"x")
        with self.assertRaises(KeyError):
            self.store.save_media("nobody", "a.png", b"x")

    def test_values_what_the_code_kept_and_delete(self) -> None:
        self.store.save(Widget("goal", fields=FIELDS))
        self.store.set_values("goal", {"title": "Hi", "gone_field": 1})
        self.assertEqual(self.store.get("goal").field_data()["title"], "Hi")
        self.assertNotIn("gone_field", self.store.get("goal").field_data())  # a field the code no longer has
        self.assertIsNone(self.store.kept("goal", "count"))
        self.store.keep("goal", "count", {"value": 3})
        self.assertEqual(WidgetStore(self.folder).kept("goal", "count"), {"value": 3})
        self.assertEqual(list(self.store.data_files("goal")), ["store.json"])  # in the widget's data folder
        self.assertTrue((self.folder / "goal" / "data" / "store.json").is_file())
        self.store.delete("goal")
        self.assertEqual((self.store.names(), self.store.get("goal")), ([], None))
        with self.assertRaisesRegex(KeyError, "no widget"):
            self.store.set_values("goal", {})

    def test_the_example_widget_comes_with_the_toolbox(self) -> None:
        name = self.store.add_example()
        example = self.store.get(name)
        self.assertIn("{{title}}", example.html)
        self.assertIn("onEventReceived", example.js)
        self.assertEqual(example.field_data()["title"], "Latest follower")
        self.store.set_values(name, {"title": "Mine"})
        self.assertEqual(self.store.add_example(), name)  # there already: his changes stay
        self.assertEqual(self.store.get(name).field_data()["title"], "Mine")

    def test_a_name_cant_lead_out_of_the_widgets_folder(self) -> None:
        outside = Path(self._dir.name) / "keep.txt"
        outside.write_text("mine")
        for name in ("..", "../keep.txt", "a/b", "", "with space"):
            self.assertIsNone(self.store.get(name))
            self.store.delete(name)
            with self.assertRaisesRegex(ValueError, "letters, digits"):
                check_name(name)
        self.assertTrue(outside.is_file())

    def test_the_fields_part_as_pasted(self) -> None:
        self.assertEqual(parse_fields("  "), {})
        self.assertEqual(parse_fields('{"a": {"type": "text"}}'), {"a": {"type": "text"}})
        with self.assertRaisesRegex(ValueError, "isn't JSON"):
            parse_fields("{a: 1}")
        with self.assertRaisesRegex(ValueError, "must look like"):
            parse_fields('{"a": "text"}')


if __name__ == "__main__":
    unittest.main()
