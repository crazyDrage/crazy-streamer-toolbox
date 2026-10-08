import unittest

from streamer_toolbox.gui.components.app_shell import AppShell
from streamer_toolbox.gui.services.open_pages import OpenPages
from streamer_toolbox.gui.services.ui_registry import UiRegistry


class TestAppShellLeftOut(unittest.TestCase):
    """What a build's menu lists when pages are left out (not tested yet). The drawing itself needs a browser."""

    def setUp(self) -> None:
        self.shell = AppShell(UiRegistry(), OpenPages())
        self.shell.sub_items["/overlays"] = [("Alerts", "/overlays?show=alerts", "campaign"),
                                             ("Widgets", "/overlays?show=widgets", "widgets")]
        self.shell.sub_items["/tools"] = lambda: [("Points", "/tools?show=points", "toll")]

    def test_nothing_is_left_out_in_the_project_folder(self) -> None:
        for path in ("/", "/variables", "/overlays", "/overlays?show=alerts"):
            self.assertTrue(self.shell.offers(path))
            self.assertTrue(self.shell.in_menu(path))

    def test_an_untested_page_is_not_in_the_menu_and_its_address_is_not_offered(self) -> None:
        self.shell.left_out = {"/variables", "/overlays?show=alerts"}
        self.assertFalse(self.shell.in_menu("/variables"))
        self.assertFalse(self.shell.offers("/variables"))
        self.assertTrue(self.shell.in_menu("/"))  # a tested page stays
        self.assertTrue(self.shell.offers("/"))
        self.assertFalse(self.shell.offers("/overlays?show=alerts"))
        self.assertTrue(self.shell.offers("/overlays"))
        self.assertEqual([title for title, _, _ in self.shell._below("/overlays")], ["Widgets"])

    def test_an_untested_area_keeps_its_row_while_something_is_below_it(self) -> None:
        self.shell.left_out = {"/tools", "/overlays", "/overlays?show=alerts", "/overlays?show=widgets"}
        self.assertTrue(self.shell.in_menu("/tools"))  # the Points tool is still there
        self.assertFalse(self.shell.offers("/tools"))  # its own main view is not
        self.assertFalse(self.shell.in_menu("/overlays"))


if __name__ == "__main__":
    unittest.main()
