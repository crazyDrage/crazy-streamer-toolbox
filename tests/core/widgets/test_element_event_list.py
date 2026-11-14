import unittest

from streamer_toolbox.core.widgets.element_design import ElementDesign
from streamer_toolbox.core.widgets.entry_table import EntryTable


class TestElementEventList(unittest.TestCase):
    def setUp(self):
        self.design = ElementDesign.new()
        self.name = self.design.add(0, "eventList")

    def test_a_new_list_has_its_usual_settings_and_no_events(self):
        found = self.design.event_list(0, self.name)
        self.assertEqual("List", self.name)
        self.assertEqual((10, 8, "top", 0, True), (found["count"], found["gap"], found["newest"],
                                                   found["stays"], found["keep"]))
        self.assertNotIn("pictures", found)  # a profile picture comes from the flow, as an event value
        self.assertEqual([], found["entries"])
        self.assertEqual("600px", self.design.piece(0, self.name)["style"]["height"])

    def test_settings_are_kept_within_bounds(self):
        self.design.set_event_list(0, self.name, count=500, gap=-3, newest="sideways", stays=12)
        found = self.design.event_list(0, self.name)
        self.assertEqual((100, 0, "top", 12), (found["count"], found["gap"], found["newest"], found["stays"]))

    def test_an_event_gets_a_first_look_that_says_what_happened(self):
        self.design.add_list_event(0, self.name, "follower")
        table = self.design.list_entry(0, self.name, "follower")
        self.assertEqual("{user} followed", table.cell(0)["text"])
        with self.assertRaises(ValueError):
            self.design.add_list_event(0, self.name, "follower")
        with self.assertRaises(ValueError):
            self.design.add_list_event(0, self.name, "redeem")

    def test_a_changed_look_is_kept(self):
        self.design.add_list_event(0, self.name, "message")
        table = self.design.list_entry(0, self.name, "message")
        table.add(0, "left")
        table.set_cell(1, kind="image", address="{picture}")
        self.design.set_list_entry(0, self.name, "message", table)
        self.assertEqual("image", self.design.list_entry(0, self.name, "message").cell(1)["kind"])
        self.assertEqual({"{picture}"}, self.design.addresses())

    def test_a_value_typed_as_a_colour_stays_as_typed(self):
        # his: {color} typed in a chat message's colour field (the value's own name, his 11-13)
        self.design.add_list_event(0, self.name, "message")
        table = self.design.list_entry(0, self.name, "message")
        table.set_style(0, color="{color}")
        self.design.set_list_entry(0, self.name, "message", table)
        self.assertEqual("{color}", self.design.list_entry(0, self.name, "message").cell(0)["style"]["color"])

    def test_the_first_lists_codes_are_the_values_names(self):
        # a look saved before 11-13: {event.data.username}, amount per event, {event.data.time} (no event has it)
        self.design.add_list_event(0, self.name, "cheer")
        table = self.design.list_entry(0, self.name, "cheer")
        table.set_cell(0, text="{event.data.username} cheered {event.data.amount} at {event.data.time}")
        table.set_style(0, color="{event.data.color}")
        self.design.set_list_entry(0, self.name, "cheer", table)
        table = self.design.list_entry(0, self.name, "cheer")
        self.assertEqual("{user} cheered {bits} at ", table.cell(0)["text"])
        self.assertEqual("{color}", table.cell(0)["style"]["color"])

    def test_each_event_keeps_its_values_for_the_widget_page(self):
        self.design.add_list_event(0, self.name, "raid")
        self.design.set_list_values(lambda event: [{"name": "viewers", "aka": ["amount"], "default": "1"}])
        entry = self.design.event_list(0, self.name)["entries"][0]
        self.assertEqual([{"name": "viewers", "aka": ["amount"], "default": "1"}], entry["values"])

    def test_the_widget_gets_the_events_its_list_shows(self):
        self.design.add_list_event(0, self.name, "message")
        self.design.add_list_event(0, self.name, "raid")
        self.design.set_list_event_on(0, self.name, "raid", False)
        self.assertEqual({"message"}, self.design.events())
        self.design.remove_list_event(0, self.name, "message")
        self.assertEqual(set(), self.design.events())

    def test_files_in_its_cells_are_the_widgets(self):
        self.design.add_list_event(0, self.name, "follower")
        table = self.design.list_entry(0, self.name, "follower")
        table.set_cell(0, kind="image", file="heart.gif")
        self.design.set_list_entry(0, self.name, "follower", table)
        self.assertEqual({"heart.gif"}, self.design.files())

    def test_broken_saved_entries_are_left_out_or_mended(self):
        self.design.piece(0, self.name)["toolbox"]["list"]["entries"] = [
            {"event": "follower", "table": None}, {"event": "nonsense"}, "x"]
        entries = self.design.event_list(0, self.name)["entries"]
        self.assertEqual(["follower"], [entry["event"] for entry in entries])
        self.assertEqual(EntryTable.new().data["columns"], entries[0]["table"]["columns"])


if __name__ == "__main__":
    unittest.main()
