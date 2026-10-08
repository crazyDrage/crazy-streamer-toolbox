"""The test record (docs/tested/, see TestList and TestInventory): its files, and the window to tick them in.

    $env:PYTHONPATH = "src"; .venv\\Scripts\\python.exe -m streamer_toolbox.devtools.tested
        writes a row for everything the toolbox has, sorted like its side menu, and the README's table.
        Ticks, days and notes that are in the files stay; a row whose thing is gone stays, marked.
    ... -m streamer_toolbox.devtools.tested checked box:obs.set_scene tool:points
        "AI checked" for these rows: today (Hex tried them in the running toolbox). `unchecked` takes it back.
    ... -m streamer_toolbox.devtools.tested window [port] [--no-open]
        the test window (see TestWindow; test-window.bat / test-window.sh start it): a small page of its own
        on port 8849, opened in the browser (not with --no-open), to tick next to the running toolbox. It only reads and writes
        docs/tested, so it needs no toolbox and stays open while that is restarted.

Making the files puts the toolbox together without starting it (nothing connects, no port is opened), with an
empty config in a throwaway folder: the record is about the project, not about what is switched on in config/.
"""
import argparse
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
WINDOW_PORT = 8849


def write_files(scratch: Path, arguments: list[str]) -> None:
    from streamer_toolbox.assembly.toolbox_assembly import assemble
    from streamer_toolbox.core.config.toolbox_config import ToolboxConfig

    config = scratch / "config" / "toolbox.toml"
    gate, _ = assemble(argparse.Namespace(config=config, port=None, plugins=REPO / "plugins", open="none",
                                          child=True), ToolboxConfig.read(config))
    items = gate.items()
    gate.tested.sync(items)
    if arguments[:1] in (["checked"], ["unchecked"]):
        for key in arguments[1:]:
            gate.tested.set_ai_checked(key, arguments[0] == "checked")
    print(f"docs/tested: {len(items)} rows, {len([i for i in items if gate.tested.tested(i.key)])} tested")


def show_window(port: int, open_it: bool) -> None:
    from nicegui import ui

    from streamer_toolbox.core.testing.test_list import TestList
    from streamer_toolbox.devtools.tested.test_window import TestWindow

    ui.page("/", title="Test window · crazy-streamer-toolbox")(lambda: TestWindow(TestList).build())
    ui.run(host="127.0.0.1", port=port, title="Test window", show=open_it, reload=False)


if __name__ in {"__main__", "__mp_main__"}:
    with tempfile.TemporaryDirectory() as folder:
        os.environ["NICEGUI_STORAGE_PATH"] = folder  # before NiceGUI is loaded: not the toolbox's own .nicegui
        if sys.argv[1:2] == ["window"]:
            options = [option for option in sys.argv[2:] if option != "--no-open"]
            show_window(int(options[0]) if options else WINDOW_PORT, "--no-open" not in sys.argv)
        else:
            write_files(Path(folder), sys.argv[1:])
