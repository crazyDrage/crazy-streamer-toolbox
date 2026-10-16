import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.gui.pages.plugins_page import PluginsPage
from streamer_toolbox.gui.services.ui_registry import UiRegistry
from streamer_toolbox.plugins.plugin_manifest import PluginManifest
from streamer_toolbox.plugins.plugin_switches import PluginSwitches


class TestPluginsPageSideItems(unittest.TestCase):
    """The Plugins tab's side list: a row per plugin, its pages as sub rows under it."""

    def test_a_row_per_plugin_and_its_pages_below_it(self) -> None:
        registry = UiRegistry()
        registry.pages += [("Example plugin", "/plugins/example", "menu_book"), ("Hi", "/plugins/hello", "waving_hand")]
        manifests = {"example": PluginManifest("example", "Example lamp", "1.0", 2, Path("."))}
        page = PluginsPage(lambda: (["example", "hello"], {"broken": "bad"}, [], manifests), registry)
        self.assertEqual(page.side_items(), [
            ("Example lamp", "/plugins?show=example", "extension"),
            ("Example plugin", "/plugins/example", "menu_book", True),
            ("hello", "/plugins?show=hello", "extension"),
            ("Hi", "/plugins/hello", "waving_hand", True),
            ("broken", "/plugins?show=broken", "extension")])

    def test_a_plugin_that_is_off_is_not_in_it(self) -> None:
        registry = UiRegistry()
        registry.pages.append(("Hi", "/plugins/hello", "waving_hand"))
        with tempfile.TemporaryDirectory() as folder:
            switches = PluginSwitches(Path(folder) / "plugins_off.json")
            switches.switch("hello", False)
            page = PluginsPage(lambda: (["example", "hello"], {}, ["sleepy"], {}), registry, switches)
            self.assertEqual(page.side_items(), [("example", "/plugins?show=example", "extension")])


if __name__ == "__main__":
    unittest.main()
