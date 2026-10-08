import importlib
import importlib.metadata
import importlib.util
import inspect
import logging
import sys
import types
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, Optional

from streamer_toolbox.core.interfaces.plugin_context import PluginContext
from streamer_toolbox.plugins.plugin_manifest import MANIFEST, PluginManifest
from streamer_toolbox.core.interfaces.toolbox_plugin import ToolboxPlugin

API_VERSION = 2  # 2 added connections, triggers, events and full boxes; a plugin made for 1 still loads
ENTRY_POINT_GROUP = "streamer_toolbox.plugins"
PACKAGE_ROOT = "toolbox_plugins"
log = logging.getLogger(__name__)


def installed_entry_points() -> Iterable[Any]:
    return importlib.metadata.entry_points(group=ENTRY_POINT_GROUP)


class PluginLoader:
    """Loads plugins from plugins/<id>/ folders (plugin.json + main.py, see PluginManifest) and from installed
    entry points. context_factory(plugin_id, folder) makes each one's PluginContext (folder is None for an
    installed plugin).

    A plugin that fails to import or register is recorded in `failed` and skipped; it never stops the toolbox.
    """

    def __init__(
        self,
        folder: Path,
        context_factory: Callable[[str, Optional[Path]], PluginContext],
        entry_points: Callable[[], Iterable[Any]] = installed_entry_points,
    ) -> None:
        self._folder = folder
        self._context_factory = context_factory
        self._entry_points = entry_points
        self.loaded: list[str] = []
        self.failed: dict[str, str] = {}
        self.disabled: list[str] = []  # found but not in the enable list
        self.manifests: dict[str, PluginManifest] = {}  # folder plugins by id, whatever their status

    def load_all(self, enabled: Optional[set[str]] = None) -> None:
        """Load every plugin found, or only those whose id is in `enabled`."""
        for manifest_path in sorted(self._folder.glob(f"*/{MANIFEST}")):
            self._load_folder(manifest_path, enabled)
        for old in sorted(self._folder.glob("*/plugin.toml")):
            if not (old.parent / MANIFEST).exists():
                self._fail(old.parent.name, f"old plugin.toml: plugins now need {MANIFEST} and main.py "
                                            "(see docs/PLUGINS.md)")
        for entry_point in self._entry_points():
            if enabled is None or entry_point.name in enabled:
                self._register(entry_point.name, entry_point.load)
            else:
                self.disabled.append(entry_point.name)

    def _load_folder(self, manifest_path: Path, enabled: Optional[set[str]]) -> None:
        try:
            manifest = PluginManifest.read(manifest_path)
        except Exception as e:
            self._fail(manifest_path.parent.name, f"bad {MANIFEST}: {e}")
            return
        self.manifests.setdefault(manifest.id, manifest)
        if enabled is not None and manifest.id not in enabled:
            self.disabled.append(manifest.id)
            return
        if not 1 <= manifest.api_version <= API_VERSION:
            self._fail(manifest.id, f"made for api_version {manifest.api_version}, toolbox has {API_VERSION}")
            return
        self._register(manifest.id, lambda: self._import_folder_plugin(manifest), manifest.folder)

    def _import_folder_plugin(self, manifest: PluginManifest) -> type:
        # plugins/<id>/ becomes the package toolbox_plugins.<id>, so plugins can use relative imports
        if PACKAGE_ROOT not in sys.modules:
            root = types.ModuleType(PACKAGE_ROOT)
            root.__path__ = []
            sys.modules[PACKAGE_ROOT] = root
        package = f"{PACKAGE_ROOT}.{manifest.id}"
        init = manifest.folder / "__init__.py"
        if init.exists():
            spec = importlib.util.spec_from_file_location(
                package, init, submodule_search_locations=[str(manifest.folder)])
            module = importlib.util.module_from_spec(spec)
            sys.modules[package] = module
            spec.loader.exec_module(module)
        else:
            module = types.ModuleType(package)
            module.__path__ = [str(manifest.folder)]
            sys.modules[package] = module
        main = importlib.import_module(f"{package}.{Path(manifest.main).stem}")
        if manifest.class_name:
            return getattr(main, manifest.class_name)
        found = [c for _, c in inspect.getmembers(main, inspect.isclass)
                 if c.__module__ == main.__name__ and issubclass(c, ToolboxPlugin) and not inspect.isabstract(c)]
        if len(found) != 1:
            raise TypeError(f"{manifest.main} needs exactly one ToolboxPlugin class (found {len(found)}); "
                            f"or name it in {MANIFEST} as \"class\"")
        return found[0]

    def _register(self, plugin_id: str, load_class: Callable[[], type], folder: Optional[Path] = None) -> None:
        if plugin_id in self.loaded:
            self._fail(plugin_id, "a plugin with this id is already loaded")
            return
        try:
            plugin = load_class()()
            if not isinstance(plugin, ToolboxPlugin):
                raise TypeError(f"{type(plugin).__name__} is not a ToolboxPlugin")
            plugin.register(self._context_factory(plugin_id, folder))
        except Exception as e:
            self._fail(plugin_id, f"{type(e).__name__}: {e}")
            return
        self.loaded.append(plugin_id)
        log.info("plugin %s loaded", plugin_id)

    def _fail(self, plugin_id: str, reason: str) -> None:
        self.failed[plugin_id] = reason
        log.warning("plugin %s not loaded: %s", plugin_id, reason)
