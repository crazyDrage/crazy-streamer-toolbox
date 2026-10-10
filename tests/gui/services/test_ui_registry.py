import unittest

from streamer_toolbox.gui.services.ui_registry import UiRegistry


class TestUiRegistry(unittest.TestCase):
    def test_panels_are_picked_by_section(self) -> None:
        registry = UiRegistry()
        live, settings = (lambda: None), (lambda: None)
        registry.panels += [("hello", "live", "Badge", live), ("hello", "settings", "Options", settings)]
        self.assertEqual(registry.panels_for("settings"), [("hello", "Options", settings)])
        self.assertEqual(registry.panels_for("connections"), [])


if __name__ == "__main__":
    unittest.main()
