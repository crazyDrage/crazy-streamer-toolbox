import tempfile
import unittest
import uuid
from pathlib import Path

import httpx

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.plugins.plugin_loader import PluginLoader
from streamer_toolbox.plugins.plugin_template import PluginTemplate, id_of
from tests.fakes.fake_plugin_context import FakePluginContext


class TestPluginTemplate(unittest.IsolatedAsyncioTestCase):
    """The "New plugin" button (his round 57): what it makes loads as it is and its first box works."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.template = PluginTemplate(self.folder)
        self.actions = ActionRegistry()
        self.name = f"Test {uuid.uuid4().hex[:8]}"  # loaded plugin modules stay in sys.modules: an id each

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _load(self) -> PluginLoader:
        def make_context(plugin_id: str, folder) -> FakePluginContext:
            ctx = FakePluginContext(plugin_id, self.actions, folder=folder)
            ctx.transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"args": {"text": "hi"}}))
            return ctx

        loader = PluginLoader(self.folder, make_context, lambda: [])
        loader.load_all()
        return loader

    async def test_one_with_code_loads_and_its_first_box_says_hello(self) -> None:
        folder = self.template.make(self.name, with_code=True)
        loader = self._load()
        self.assertEqual((loader.loaded, loader.failed), ([folder.name], {}))
        self.assertEqual(await self.actions.run(f"{folder.name}.say_hello", name="Ann"), {"text": "Hello Ann!"})
        self.assertEqual(loader.manifests[folder.name].name, self.name)

    async def test_one_without_code_loads_and_its_first_web_box_works(self) -> None:
        folder = self.template.make(self.name, with_code=False)
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ["boxes", "plugin.json"])
        loader = self._load()
        self.assertEqual((loader.loaded, loader.failed), ([folder.name], {}))
        self.assertEqual(await self.actions.run(f"{folder.name}.echo", text="hi"), {"text": "hi"})

    def test_a_name_twice_or_without_letters_is_refused(self) -> None:
        self.template.make(self.name, with_code=True)
        with self.assertRaisesRegex(ValueError, "already"):
            self.template.make(self.name, with_code=False)
        with self.assertRaisesRegex(ValueError, "letters"):
            self.template.make(" !? ", with_code=True)

    def test_the_id_comes_from_the_name(self) -> None:
        self.assertEqual((id_of("My Weather!"), id_of("2 Good"), id_of("Ünïcode-Box")),
                         ("my_weather", "plugin_2_good", "unicode_box"))


if __name__ == "__main__":
    unittest.main()
