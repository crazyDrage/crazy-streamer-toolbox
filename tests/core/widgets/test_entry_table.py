import unittest

from streamer_toolbox.core.widgets.entry_table import EntryTable


def spots(table: EntryTable) -> list[tuple[int, int, int, int]]:
    """Each cell as (col, row, cols, rows)."""
    return [(c["col"], c["row"], c["cols"], c["rows"]) for c in table.cells()]


def picture(table: EntryTable) -> list[str]:
    """The table as rows of cell numbers, "." for an empty spot."""
    seen = [["."] * table.data["columns"] for _ in range(table.data["rows"])]
    for number, c in enumerate(table.cells()):
        for row in range(c["row"], c["row"] + c["rows"]):
            for col in range(c["col"], c["col"] + c["cols"]):
                seen[row][col] = str(number) if seen[row][col] == "." else "!"  # ! two cells on one spot
    return ["".join(line) for line in seen]


def cell(col, row, cols, rows, text="x"):
    return {"col": col, "row": row, "cols": cols, "rows": rows, "kind": "text", "text": text, "file": "",
            "style": {}}


def his_table() -> EntryTable:
    """His (2026-11-13): 1 on the left all the way down, 2 top right, nothing in the middle, 3 bottom right."""
    return EntryTable.of({"columns": 2, "rows": 3, "style": {},
                          "cells": [cell(0, 0, 1, 3, "1"), cell(1, 0, 1, 1, "2"), cell(1, 2, 1, 1, "3")]})


class TestEntryTable(unittest.TestCase):
    def test_a_new_table_is_one_text_cell_with_the_name(self):
        table = EntryTable.new()
        self.assertEqual([(0, 0, 1, 1)], spots(table))
        self.assertEqual("{user}", table.cell(0)["text"])

    def test_a_cell_on_the_right(self):
        table = EntryTable.new()
        new = table.add(0, "right")
        self.assertEqual(["01"], picture(table))
        self.assertEqual(1, new)
        self.assertEqual(2, table.data["columns"])

    def test_a_cell_on_the_left_moves_it_along(self):
        table = EntryTable.new()
        table.add(0, "left")
        self.assertEqual(["10"], picture(table))

    def test_a_new_line_leaves_the_others_spots_in_it_empty(self):
        table = EntryTable.new()
        table.add(0, "right")
        table.add(0, "bottom")  # the message under the name only
        self.assertEqual(["01", "2."], picture(table))

    def test_a_new_line_through_a_wide_cell_widens_it(self):
        table = EntryTable.new()
        table.add(0, "right")
        table.add(0, "bottom")
        table.join(2, "right")  # the bottom one is two wide
        table.add(0, "right")  # a new column between the two top cells
        self.assertEqual(["031", "222"], picture(table))

    def test_moving_left_goes_to_the_column_there_and_makes_nothing_new(self):
        table = his_table()
        self.assertEqual(["01", "0.", "02"], picture(table))
        table.move(2, "left")  # 3 into the first column: 1 gets shorter, 3's old spot is empty
        self.assertEqual(["01", "0.", "2."], picture(table))
        self.assertEqual(3, len(table.cells()))
        self.assertEqual("3", table.cell(2)["text"])

    def test_moving_up_and_down_goes_to_another_row(self):
        table = his_table()
        table.move(2, "top")  # into the empty spot
        self.assertEqual(["01", "02", "0."], picture(table))
        table.move(2, "top")  # where 2 was: 2 takes its old place
        self.assertEqual(["02", "01", "0."], picture(table))
        self.assertEqual(("2", "3"), (table.cell(1)["text"], table.cell(2)["text"]))

    def test_moving_two_cells_past_each_other(self):
        table = EntryTable.new("name")
        table.add(0, "bottom")
        table.add(0, "right")
        self.assertEqual(["02", "1."], picture(table))
        table.move(1, "right")
        self.assertEqual(["02", ".1"], picture(table))
        table.move(1, "top")  # a cell the same size: they change places
        self.assertEqual(["01", ".2"], picture(table))

    def test_moving_at_the_edge_makes_nothing(self):
        table = EntryTable.new("name")
        message = table.add(0, "bottom")
        table.add(0, "right")
        for side in ("bottom", "left"):
            with self.assertRaises(ValueError):
                table.move(message, side)
        self.assertEqual(["02", "1."], picture(table))
        with self.assertRaises(ValueError):
            table.move(0, "up")

    def test_a_wide_cell_moves_too(self):
        table = EntryTable.new("name")
        table.add(0, "right")
        bottom = table.add(0, "bottom")
        table.join(bottom, "right")
        table.move(bottom, "top")  # the two above it go under it
        self.assertEqual(["22", "01"], picture(table))

    def test_joining_grows_over_the_next_line(self):
        table = EntryTable.new()
        table.add(0, "right")
        table.set_cell(0, text="kept")
        table.join(0, "right")
        self.assertEqual(["0"], picture(table))
        self.assertEqual("kept", table.cell(0)["text"])

    def test_joining_two_in_a_row_leaves_the_other_rows_columns(self):
        table = EntryTable.new("a")
        table.add(0, "right")
        table.add(0, "bottom")
        table.add(1, "bottom")  # on the empty spot under it
        self.assertEqual(["01", "23"], picture(table))
        table.join(2, "right")
        self.assertEqual(["01", "22"], picture(table))
        self.assertEqual(2, table.data["columns"])

    def test_joining_over_a_cell_that_reaches_further_makes_it_smaller(self):
        table = his_table()
        table.join(1, "left")  # 2 over the top of 1
        self.assertEqual(["11", "0.", "02"], picture(table))
        table.join(2, "top")  # 3 over the empty spot
        self.assertEqual(["11", "02"], picture(table))

    def test_an_empty_cell_takes_what_it_joins_over(self):
        table = EntryTable.new("name")
        empty = table.add(0, "left")
        table.join(empty, "right")
        self.assertEqual([(0, 0, 1, 1)], spots(table))
        self.assertEqual("name", table.cell(0)["text"])

    def test_joining_at_the_edge(self):
        with self.assertRaises(ValueError):
            EntryTable.new().join(0, "top")

    def test_removing_always_works_and_leaves_its_spots_empty(self):
        table = his_table()
        table.remove(0)  # the tall one: its column is empty all along and goes
        self.assertEqual(["0", "1"], picture(table))  # the empty row goes too
        table = his_table()
        table.remove(1)
        self.assertEqual(["0.", "01"], picture(table))

    def test_the_last_cell_stays(self):
        with self.assertRaises(ValueError):
            EntryTable.new().remove(0)

    def test_a_cell_on_an_empty_spot(self):
        table = his_table()
        self.assertEqual([(1, 1)], table.empty_spots())
        new = table.put(1, 1)
        self.assertEqual(["01", "03", "02"], picture(table))
        self.assertEqual([], table.empty_spots())
        with self.assertRaises(ValueError):
            table.put(new, 0)

    def test_cells_on_top_of_each_other_are_put_right(self):
        # his `testing` table: the message lay over the picture and the name
        table = EntryTable.of({"columns": 4, "rows": 4, "style": {}, "cells": [
            cell(0, 0, 1, 3, ""), cell(0, 2, 3, 2, "message"), cell(1, 0, 1, 3, "name"), cell(2, 0, 1, 2, ""),
            cell(2, 1, 1, 2, ""), cell(3, 0, 1, 4, "")]})
        self.assertNotIn("!", "".join(picture(table)))
        self.assertEqual(["message", "name"], [c["text"] for c in table.cells() if c["text"]])

    def test_cell_contents_and_looks(self):
        table = EntryTable.new()
        table.set_cell(0, kind="image")
        table.set_style(0, width="64px")
        table.set_style(None, backgroundColor=None)
        self.assertEqual("image", table.cell(0)["kind"])
        self.assertEqual("64px", table.cell(0)["style"]["width"])
        self.assertNotIn("backgroundColor", table.data["style"])
        with self.assertRaises(ValueError):
            table.set_cell(0, kind="sound")

    def test_files_of_the_media_folder(self):
        table = EntryTable.new()
        table.add(0, "left")
        table.set_cell(1, kind="image", file="heart.gif")
        table.set_cell(0, kind="image", file="https://example.org/x.png")
        self.assertEqual({"heart.gif"}, table.files())

    def test_addresses_of_picture_cells(self):
        table = EntryTable.new()
        table.add(0, "left")
        table.set_cell(1, kind="image", address=r" C:\pics\{user}.png ")
        table.set_cell(0, address="https://not.a.picture/cell")  # a text cell's address doesn't count
        self.assertEqual({r"C:\pics\{user}.png"}, table.addresses())

    def test_the_first_lists_profile_picture_cell_is_a_picture_with_that_value(self):
        table = EntryTable.of({"columns": 1, "rows": 1, "style": {},
                               "cells": [{"col": 0, "row": 0, "cols": 1, "rows": 1, "kind": "picture", "text": "",
                                          "file": "", "style": {}}]})
        self.assertEqual(("image", "{picture}"), (table.cell(0)["kind"], table.cell(0)["address"]))

    def test_broken_settings_give_a_new_table(self):
        self.assertEqual([(0, 0, 1, 1)], spots(EntryTable.of({"cells": []})))
        self.assertEqual([(0, 0, 1, 1)], spots(EntryTable.of(None)))


if __name__ == "__main__":
    unittest.main()
