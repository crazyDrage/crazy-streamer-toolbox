import unittest

from streamer_toolbox.core.widgets.field_list import FieldList

FIELDS = {"title": {"type": "text", "label": "Title", "value": "Hi", "group": "Text"},
          "size": {"type": "slider", "label": "Size", "value": 32, "min": 10, "max": 100}}


class TestFieldList(unittest.TestCase):
    def test_add_rename_up_and_remove_keep_the_order(self) -> None:
        fields = FieldList(FIELDS)
        name = fields.add("checkbox")
        self.assertEqual((name, fields.fields[name]["value"]), ("setting1", False))
        fields.rename("size", "fontSize")
        self.assertEqual(list(fields.fields), ["title", "fontSize", "setting1"])
        fields.up("setting1")
        self.assertEqual(list(fields.fields), ["title", "setting1", "fontSize"])
        fields.remove("title")
        self.assertEqual(list(fields.fields), ["setting1", "fontSize"])
        self.assertEqual(FIELDS["size"]["min"], 10)  # the FIELDS it was made from stay as they were

    def test_a_name_the_code_cant_read_or_one_that_is_taken(self) -> None:
        fields = FieldList(FIELDS)
        for bad in ("my size", "1st", ""):
            with self.assertRaisesRegex(ValueError, "letters, digits"):
                fields.rename("size", bad)
        with self.assertRaisesRegex(ValueError, "already"):
            fields.rename("size", "title")

    def test_a_new_type_drops_what_it_cant_have(self) -> None:
        fields = FieldList(FIELDS)
        fields.set("size", "type", "colorpicker")
        self.assertEqual(fields.fields["size"], {"type": "colorpicker", "label": "Size", "value": "#ffffff"})
        fields.set("size", "type", "dropdown")
        self.assertEqual(fields.fields["size"]["options"], {"one": "One", "two": "Two"})
        fields.set("title", "type", "textarea")
        self.assertEqual(fields.fields["title"]["value"], "Hi")  # still fits: kept
        fields.set("title", "group", "")
        self.assertNotIn("group", fields.fields["title"])
        fields.set("title", "max", 1920.0)
        fields.set("title", "step", 0.5)
        self.assertEqual((fields.fields["title"]["max"], fields.fields["title"]["step"]), (1920, 0.5))

    def test_dropdown_choices_as_lines(self) -> None:
        options = FieldList.options_from("left: Left side\nright\n\n center : Middle ")
        self.assertEqual(options, {"left": "Left side", "right": "right", "center": "Middle"})
        self.assertEqual(FieldList.options_text(options), "left: Left side\nright\ncenter: Middle")


if __name__ == "__main__":
    unittest.main()
