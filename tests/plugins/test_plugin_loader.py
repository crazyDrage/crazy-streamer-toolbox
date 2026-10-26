import asyncio
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.plugins.plugin_loader import PluginLoader
from tests.fakes.fake_entry_point import FakeEntryPoint
from tests.fakes.fake_installed_plugin import FakeInstalledPlugin
from tests.fakes.fake_plugin_context import FakePluginContext
from tests.helpers.plugin_folder_builder import CRASHING_PLUGIN, NOT_A_PLUGIN, WORKING_PLUGIN, unique_id, write_plugin


class TestPluginLoader(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.actions = ActionRegistry()
        self.contexts: dict[str, FakePluginContext] = {}
        self.entry_points: list[FakeEntryPoint] = []

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _loader(self) -> PluginLoader:
        def make_context(plugin_id: str, folder) -> FakePluginContext:
            self.contexts[plugin_id] = FakePluginContext(plugin_id, self.actions, folder=folder)
            return self.contexts[plugin_id]
        return PluginLoader(self.root, make_context, lambda: self.entry_points)

    def test_folder_plugin_registers_with_relative_imports(self) -> None:
        pid = unique_id()
        write_plugin(self.root, pid, {"main.py": WORKING_PLUGIN, "lib/helper.py": 'GREETING = "hi"'})
        loader = self._loader()
        loader.load_all()
        self.assertEqual(loader.loaded, [pid])
        self.assertEqual(asyncio.run(self.actions.run(f"{pid}.greet")), "hi")
        self.assertEqual(self.contexts[pid].pages, [f"/plugins/{pid}"])
        self.assertEqual(self.contexts[pid].resources, self.root / pid / "resources")

    def test_a_folder_with_only_web_boxes_needs_no_code(self) -> None:
        pid, empty = unique_id(), unique_id()
        box = '{"boxes": [{"name": "joke", "target": {"url": "https://jokes.test/random"}}]}'
        write_plugin(self.root, pid, {"boxes/jokes.json": box}, api_version=4)
        write_plugin(self.root, empty, {"resources/settings.json": "{}"}, api_version=4)
        loader = self._loader()
        loader.load_all()
        self.assertEqual(loader.loaded, [pid])
        self.assertTrue(self.actions.get(f"{pid}.joke").flow_only)
        self.assertEqual(loader.failed, {empty: "has no main.py and no boxes/ folder"})

    def test_the_class_in_main_is_found_or_named(self) -> None:
        two = WORKING_PLUGIN + "\n\nclass Other(Plugin):\n    pass\n"
        unnamed, named = unique_id(), unique_id()
        write_plugin(self.root, unnamed, {"main.py": two, "lib/helper.py": 'GREETING = "hi"'})
        write_plugin(self.root, named, {"start.py": two, "lib/helper.py": 'GREETING = "yo"'},
                     main="start.py", **{"class": "Other"})
        loader = self._loader()
        loader.load_all()
        self.assertIn("exactly one ToolboxPlugin", loader.failed[unnamed])
        self.assertEqual(loader.loaded, [named])

    def test_an_old_plugin_toml_folder_is_reported(self) -> None:
        folder = self.root / "old"
        folder.mkdir()
        (folder / "plugin.toml").write_text('id = "old"', encoding="utf-8")
        loader = self._loader()
        loader.load_all()
        self.assertIn("plugin.json", loader.failed["old"])

    def test_crashing_plugin_is_reported_and_others_still_load(self) -> None:
        bad, good = unique_id(), unique_id()
        write_plugin(self.root, bad, {"main.py": CRASHING_PLUGIN})
        write_plugin(self.root, good, {"main.py": WORKING_PLUGIN, "lib/helper.py": 'GREETING = "hi"'})
        loader = self._loader()
        loader.load_all()
        self.assertEqual(loader.loaded, [good])
        self.assertIn("config missing", loader.failed[bad])

    def test_wrong_api_version_is_not_imported(self) -> None:
        pid = unique_id()
        write_plugin(self.root, pid, {"main.py": "raise SystemExit('must not be imported')"}, api_version=5)
        loader = self._loader()
        loader.load_all()
        self.assertEqual(loader.loaded, [])
        self.assertIn("api_version 5", loader.failed[pid])

    def test_class_must_implement_toolbox_plugin(self) -> None:
        found, named = unique_id(), unique_id()
        write_plugin(self.root, found, {"main.py": NOT_A_PLUGIN})
        write_plugin(self.root, named, {"main.py": NOT_A_PLUGIN}, **{"class": "Plugin"})
        loader = self._loader()
        loader.load_all()
        self.assertIn("exactly one ToolboxPlugin class (found 0)", loader.failed[found])
        self.assertIn("not a ToolboxPlugin", loader.failed[named])

    def test_bad_manifest_is_reported_by_folder_name(self) -> None:
        folder = self.root / "broken"
        folder.mkdir()
        (folder / "plugin.json").write_text('{"id": "broken"}', encoding="utf-8")
        loader = self._loader()
        loader.load_all()
        self.assertIn("missing", loader.failed["broken"])

    def test_enabled_list_skips_other_plugins(self) -> None:
        on, off = unique_id(), unique_id()
        for pid in (on, off):
            write_plugin(self.root, pid, {"main.py": WORKING_PLUGIN, "lib/helper.py": 'GREETING = "hi"'})
        loader = self._loader()
        loader.load_all(enabled={on})
        self.assertEqual(loader.loaded, [on])
        self.assertNotIn(off, loader.failed)
        self.assertEqual(loader.disabled, [off])

    def test_entry_point_plugin_is_loaded(self) -> None:
        self.entry_points.append(FakeEntryPoint("installed", FakeInstalledPlugin))
        loader = self._loader()
        loader.load_all()
        self.assertEqual(loader.loaded, ["installed"])
        self.assertEqual(asyncio.run(self.actions.run("installed.ping")), "pong")

    def test_duplicate_id_is_rejected(self) -> None:
        self.entry_points += [FakeEntryPoint("twice", FakeInstalledPlugin), FakeEntryPoint("twice", FakeInstalledPlugin)]
        loader = self._loader()
        loader.load_all()
        self.assertEqual(loader.loaded, ["twice"])
        self.assertIn("already loaded", loader.failed["twice"])


if __name__ == "__main__":
    unittest.main()
