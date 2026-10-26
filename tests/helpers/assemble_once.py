"""Runs assemble() once, as a start does but without opening the port, and prints every box's name as JSON.

    python -m tests.helpers.assemble_once <folder>

<folder> gets config/toolbox.toml (empty = the defaults) and an empty plugins/ folder; the toolbox writes only
there. Its own process, because assemble() changes NiceGUI's one global app (TestToolboxAssembly runs it)."""
import argparse
import json
import sys
from pathlib import Path

import streamer_toolbox.core.actions.action_registry as registry_module

made: list[registry_module.ActionRegistry] = []
_original = registry_module.ActionRegistry.__init__


def _remember(self: registry_module.ActionRegistry) -> None:
    _original(self)
    made.append(self)


registry_module.ActionRegistry.__init__ = _remember

from streamer_toolbox.assembly.toolbox_assembly import assemble  # noqa: E402  (after the patch)
from streamer_toolbox.core.config.toolbox_config import ToolboxConfig  # noqa: E402


def main() -> None:
    root = Path(sys.argv[1])
    config = root / "config" / "toolbox.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.touch()
    (root / "plugins").mkdir(exist_ok=True)
    args = argparse.Namespace(config=config, settings=None, port=None, plugins=root / "plugins", open="none",
                              child=True)
    assemble(args, ToolboxConfig.read(config))
    actions = max(made, key=lambda registry: len(registry.all(include_flow_only=True)))
    print(json.dumps([box.name for box in actions.all(include_flow_only=True)]))


if __name__ == "__main__":
    main()
