import json
from pathlib import Path


class PluginSwitches:
    """Which loaded plugins he switched off on the Plugins page (config/plugins_off.json, a list of ids). A
    plugin that is off stays loaded, so flows that already use its boxes and triggers keep working; its boxes
    and triggers are only no longer offered for adding. (Not loading a plugin at all is `[plugins] enabled`
    in the settings file.)"""

    def __init__(self, path: Path) -> None:
        self._path = path

    def off(self) -> set[str]:
        try:
            ids = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):  # no file yet, or one that can't be read: every plugin is on
            return set()
        return {str(i) for i in ids} if isinstance(ids, list) else set()

    def switch(self, plugin_id: str, on: bool) -> None:
        ids = self.off() - {plugin_id} if on else self.off() | {plugin_id}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(sorted(ids)), encoding="utf-8")
