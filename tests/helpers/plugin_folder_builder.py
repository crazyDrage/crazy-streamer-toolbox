"""Writes drop-in plugin folders (plugin.json + main.py, lib/, resources/) for the loader tests."""
import json
import uuid
from pathlib import Path


def unique_id() -> str:
    # each test gets its own id, because loaded plugin modules stay in sys.modules
    return f"p{uuid.uuid4().hex[:10]}"


def write_plugin(root: Path, plugin_id: str, files: dict[str, str], api_version: int = 1, **info) -> Path:
    """files: paths inside the plugin folder ("main.py", "lib/helper.py", "resources/settings.json")."""
    folder = root / plugin_id
    folder.mkdir(parents=True)
    manifest = {"id": plugin_id, "name": "Test", "version": "1", "api_version": api_version, **info}
    (folder / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    for name, content in files.items():
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(content, encoding="utf-8")
    return folder


WORKING_PLUGIN = '''
from streamer_toolbox.core.interfaces.toolbox_plugin import ToolboxPlugin
from .lib.helper import GREETING


class Plugin(ToolboxPlugin):
    def register(self, ctx):
        async def greet():
            return GREETING
        ctx.add_action("greet", greet)
        ctx.add_page("Page", lambda: None)
'''

CRASHING_PLUGIN = '''
from streamer_toolbox.core.interfaces.toolbox_plugin import ToolboxPlugin


class Plugin(ToolboxPlugin):
    def register(self, ctx):
        raise RuntimeError("config missing")
'''

NOT_A_PLUGIN = '''
class Plugin:
    def register(self, ctx):
        pass
'''
