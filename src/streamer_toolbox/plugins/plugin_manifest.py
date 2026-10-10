import json
import re
from dataclasses import dataclass
from pathlib import Path

ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
MAIN_PATTERN = re.compile(r"^[A-Za-z_]\w*\.py$")
CLASS_PATTERN = re.compile(r"^[A-Za-z_]\w*$")
MANIFEST = "plugin.json"


@dataclass(frozen=True)
class PluginManifest:
    """plugin.json, the info file of a drop-in plugin folder:

        plugins/<id>/
          plugin.json   {"id", "name", "version", "api_version"; optional "description", "author",
                         "main" (default "main.py"), "class" (default: the one ToolboxPlugin in main)}
          main.py       the entry point: its ToolboxPlugin's register(ctx) adds everything the plugin has
          lib/          the plugin's other Python classes (main.py: from .lib.thing import Thing)
          resources/    pictures, default settings, JS, ... (ctx.resources, ctx.resource_url)
    """

    id: str
    name: str
    version: str
    api_version: int
    folder: Path
    main: str = "main.py"
    class_name: str = ""
    description: str = ""
    author: str = ""

    @property
    def resources(self) -> Path:
        return self.folder / "resources"

    @classmethod
    def read(cls, path: Path) -> "PluginManifest":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as e:
            raise ValueError(f"{path}: not valid JSON ({e})") from e
        if not isinstance(data, dict):
            raise ValueError(f"{path}: must be a JSON object")
        missing = [k for k in ("id", "name", "version", "api_version") if k not in data]
        if missing:
            raise ValueError(f"{path}: missing {', '.join(missing)}")
        if not isinstance(data["id"], str) or not ID_PATTERN.match(data["id"]):
            raise ValueError(f"{path}: id must be lowercase letters, digits and _ (got {data['id']!r})")
        main = data.get("main", "main.py")
        if not MAIN_PATTERN.match(str(main)):
            raise ValueError(f"{path}: main must be a .py file name in the plugin folder (got {main!r})")
        class_name = str(data.get("class", ""))
        if class_name and not CLASS_PATTERN.match(class_name):
            raise ValueError(f"{path}: class must be a Python class name (got {class_name!r})")
        return cls(data["id"], str(data["name"]), str(data["version"]), int(data["api_version"]), path.parent,
                   main, class_name, str(data.get("description", "")), str(data.get("author", "")))
