import unittest

from streamer_toolbox.gui.components.app_shell import AppShell
from streamer_toolbox.gui.services.open_pages import OpenPages
from streamer_toolbox.gui.services.ui_registry import UiRegistry


class TestAppShellAreas(unittest.TestCase):
    """Which area a page is shown in, and what is below an area. The drawing itself needs a browser."""

    def setUp(self) -> None:
        self.shell = AppShell(UiRegistry(), OpenPages())
        self.shell.sub_items["/overlays"] = [("Alerts", "/overlays?show=alerts", "campaign"),
                                             ("Widgets", "/overlays?show=widgets", "widgets")]
        self.shell.sub_items["/tools"] = lambda: [("Points", "/tools?show=points", "toll")]

    def test_an_area_lists_its_sub_items_given_or_made_when_asked(self) -> None:
        self.assertEqual([title for title, _, _ in self.shell._below("/overlays")], ["Alerts", "Widgets"])
        self.assertEqual([title for title, _, _ in self.shell._below("/tools")], ["Points"])
        self.assertEqual(self.shell._below("/variables"), [])

    def test_a_plugins_page_is_shown_in_the_plugins_area_and_is_no_tab(self) -> None:
        registry = UiRegistry()
        shell = AppShell(registry, OpenPages())
        registry.pages.append(("Hello", "/plugins/hello", "waving_hand"))
        self.assertEqual(shell.area("/plugins/hello"), "/plugins")
        self.assertEqual(shell.area("/plugins/hello/more"), "/plugins")
        self.assertEqual(shell.area("/flows"), "/flows")
        self.assertEqual(shell.area("/flows/edit"), "/flows")  # an open flow keeps the Flows side list
        self.assertEqual(shell.area("/"), "/")
        self.assertEqual(shell._below("/plugins"), [("Hello", "/plugins/hello", "waving_hand")])


if __name__ == "__main__":
    unittest.main()
