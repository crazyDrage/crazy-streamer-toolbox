import json
import re
import unicodedata
from pathlib import Path

from streamer_toolbox.plugins.plugin_loader import API_VERSION, WEB_BOXES

MAIN = '''"""{name}: the entry point. register(ctx) adds everything the plugin has, one class per thing.

How: docs/PLUGINS.md. One of every kind (a trigger, a connection, a tool, ...): plugins/example/."""
from streamer_toolbox.core.interfaces.plugin_context import PluginContext
from streamer_toolbox.core.interfaces.toolbox_plugin import ToolboxPlugin

from .lib.say_hello import SayHello


class {cls}Plugin(ToolboxPlugin):
    def register(self, ctx: PluginContext) -> None:
        ctx.add(SayHello())
'''

FIRST_BOX = '''from streamer_toolbox.core.interfaces.box import Box


class SayHello(Box):
    """Your first box: change it, or copy this file for the next one (one box per file)."""

    name = "say_hello"           # its full name is "{id}.say_hello"; flows keep it, so don't rename it later
    label = "Say hello"          # its title in the Add box window
    help = "Gives back a greeting"
    outputs = {{"text": "text"}}   # the keys of what run gives back: dots other boxes can wire from

    async def run(self, name: str = "chat") -> dict[str, str]:   # its parameters are the box's fields
        return {{"text": f"Hello {{name}}!"}}
'''


class PluginTemplate:
    """Makes a new plugin folder that loads as it is (the "New plugin" button on the Plugins page): with code
    (plugin.json, main.py, lib/ with a first box) or without (plugin.json and boxes/ with a first web box)."""

    def __init__(self, folder: Path) -> None:
        self._folder = folder

    def make(self, name: str, with_code: bool) -> Path:
        """The new folder (plugins/<id>). ValueError when the name gives no id or the folder is there."""
        plugin_id = id_of(name)
        target = self._folder / plugin_id
        if target.exists():
            raise ValueError(f"There is a plugin folder {plugin_id} already: pick another name")
        files = self._with_code(name, plugin_id) if with_code else self._without_code(name, plugin_id)
        for path, text in files.items():
            (target / path).parent.mkdir(parents=True, exist_ok=True)
            (target / path).write_text(text, encoding="utf-8")
        return target

    @staticmethod
    def _info(name: str, plugin_id: str, description: str) -> str:
        return json.dumps({"id": plugin_id, "name": name.strip(), "version": "0.1.0", "api_version": API_VERSION,
                           "description": description, "author": ""}, indent=2) + "\n"

    def _with_code(self, name: str, plugin_id: str) -> dict[str, str]:
        cls = "".join(part.capitalize() for part in plugin_id.split("_"))
        return {"plugin.json": self._info(name, plugin_id, "What it does, in one sentence"),
                "main.py": MAIN.format(name=" ".join(name.split()).replace('"', "'").replace("\\", "/"), cls=cls),
                "lib/__init__.py": "",
                "lib/say_hello.py": FIRST_BOX.format(id=plugin_id)}

    def _without_code(self, name: str, plugin_id: str) -> dict[str, str]:
        first = {"group": name.strip(),
                 "boxes": [{"name": "echo", "label": "Echo",
                            "help": "Sends a text to httpbin.org, which sends it back. Change the target to your API",
                            "target": {"method": "GET", "url": "https://httpbin.org/get"},
                            "input": [{"name": "text", "hint": "Anything"}],
                            "output": {"text": "args.text"}}]}
        return {"plugin.json": self._info(name, plugin_id, "Boxes for a web API, without code"),
                f"{WEB_BOXES}/{plugin_id}.json": json.dumps(first, indent=2) + "\n"}


def id_of(name: str) -> str:
    """A plugin's id from its name: "My Weather!" → "my_weather" (lowercase letters, digits and _; "ü" → "u")."""
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    plugin_id = re.sub(r"[^a-z0-9]+", "_", plain.strip().lower()).strip("_")
    if not plugin_id:
        raise ValueError("Give the plugin a name with letters in it")
    return plugin_id if plugin_id[0].isalpha() else f"plugin_{plugin_id}"
