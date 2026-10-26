import unittest

from streamer_toolbox.gui.services.ui_registry import UiRegistry


class TestUiRegistry(unittest.TestCase):
    def test_panels_are_picked_by_section(self) -> None:
        registry = UiRegistry()
        live, settings = (lambda: None), (lambda: None)
        registry.panels += [("hello", "live", "Badge", live), ("hello", "settings", "Options", settings)]
        self.assertEqual(registry.panels_for("settings"), [("hello", "Options", settings)])
        self.assertEqual(registry.panels_for("connections"), [])

    def test_a_switched_off_plugin_has_no_cards_and_no_tools(self) -> None:
        registry = UiRegistry()
        draw = lambda: None  # noqa: E731
        registry.panels += [("hello", "settings", "Options", draw), ("lamp", "settings", "Lamp", draw)]
        registry.tools += [("hello", "Hello", "", "", draw), ("toolbox", "Points", "", "", draw)]
        registry.is_off = lambda plugin_id: plugin_id == "hello"
        self.assertEqual(registry.panels_for("settings"), [("lamp", "Lamp", draw)])
        self.assertEqual([title for _, title, *_ in registry.tools_on()], ["Points"])


if __name__ == "__main__":
    unittest.main()
