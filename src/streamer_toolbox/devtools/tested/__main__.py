"""The test record (docs/tested/, see TestList and TestInventory): its files, and the window to tick them in.

    $env:PYTHONPATH = "src"; .venv\\Scripts\\python.exe -m streamer_toolbox.devtools.tested
        writes a row for everything the toolbox has, sorted like its side menu, and the README's table;
        also the manual's public page docs/manual/user/tried.md (TriedPage, his 11-21).
        Ticks, days and notes that are in the files stay; a row whose thing is gone stays, marked.
    ... -m streamer_toolbox.devtools.tested checked box:obs.set_scene tool:points
        "AI checked" for these rows: today (Hex tried them in the running toolbox). `unchecked` takes it back.
    ... -m streamer_toolbox.devtools.tested from-flows "Flow name" other_flow [--flows <folder>] [--checks works,usable]
        [--only warudo,connection] (only rows whose name starts so: "the Warudo ones")
        his way (11-21): every box and trigger in the named flows (file name or label) gets his checks, all three
        unless --checks says which; the note says which flow. Flows from config/flows unless --flows says.
    ... -m streamer_toolbox.devtools.tested window [port] [--no-open] [--toolbox <settings folder>]
        the test window (see TestWindow; docs/tested/test-window.bat / .sh start it): a small page of its own
        on port 8849, opened in the browser (not with --no-open), to tick next to the running toolbox. It only reads and writes
        docs/tested, so it needs no toolbox and stays open while that is restarted. With --toolbox it starts the
        test toolbox on that folder (port 8855, app window) and is tied to it (TiedToolbox): one stops, both stop.

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
TOOLBOX_PORT = 8855  # the test toolbox's


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
    if arguments[:1] == ["from-flows"]:
        from_flows(gate.tested, {item.key for item in items}, arguments[1:])
    from streamer_toolbox.devtools.tested.tried_page import TriedPage

    tried = TriedPage(REPO / "docs" / "manual" / "user" / "tried.md").write(items, gate.tested.checks)
    print(f"docs/tested: {len(items)} rows, {len([i for i in items if gate.tested.tested(i.key)])} tested; "
          f"the manual's What has been tried: {tried}")


def from_flows(tested, known: set[str], arguments: list[str]) -> None:
    """Ticks his checks for everything in the named flows (FlowChecks) and says what it did."""
    from datetime import date

    from streamer_toolbox.devtools.tested.flow_checks import ALL_CHECKS, FlowChecks

    folder, checks, names, only = REPO / "config" / "flows", list(ALL_CHECKS), [], []
    rest = iter(arguments)
    for argument in rest:
        if argument == "--flows":
            folder = Path(next(rest, ""))
        elif argument == "--only":
            only = [o.strip() for o in next(rest, "").split(",") if o.strip()]
        elif argument == "--checks":
            checks = [c.strip() for c in next(rest, "").split(",") if c.strip()]
        else:
            names.append(argument)
    flows, missing = FlowChecks(folder).find(names)
    for name in missing:
        print(f"no flow {name!r} in {folder}")
    for key, labels in FlowChecks.keys(flows).items():
        if only and not key.partition(":")[2].startswith(tuple(only)):
            print(f"  left out {key} (not in --only)")
            continue
        if key not in known:
            print(f"  skipped {key} (no row in the test record)")
            continue
        for check in checks:
            tested.set_check(key, check, True)
        said = f"his {date.today().isoformat()}: {', '.join(checks)} in flow " + ", ".join(f'"{l}"' for l in labels)
        old = tested.note(key)
        if said not in old:  # the same flow named again: no second note
            tested.set_note(key, f"{old}; {said}" if old else said)
        print(f"  {key}: {', '.join(checks)}")


def show_window(port: int, open_it: bool, toolbox: Path | None = None) -> None:
    from nicegui import app, ui

    from streamer_toolbox.core.testing.test_list import TestList
    from streamer_toolbox.devtools.tested.test_window import TestWindow
    from streamer_toolbox.devtools.tested.tied_toolbox import TiedToolbox

    ui.page("/", title="Test window · crazy-streamer-toolbox")(lambda: TestWindow(TestList).build())
    if toolbox is not None:
        # its own page settings, so the two toolboxes don't write the same file
        tied = TiedToolbox([sys.executable, "-m", "streamer_toolbox", "--tied", "--settings", str(toolbox),
                            "--port", str(TOOLBOX_PORT), "--open", "window"],
                           {**os.environ, "NICEGUI_STORAGE_PATH": str(toolbox / ".nicegui")})
        app.on_startup(lambda: tied.start(app.shutdown))  # its app window closed: the test window goes too
        app.on_shutdown(tied.stop)
    ui.run(host="127.0.0.1", port=port, title="Test window", show=open_it, reload=False)


if __name__ in {"__main__", "__mp_main__"}:
    with tempfile.TemporaryDirectory() as folder:
        os.environ["NICEGUI_STORAGE_PATH"] = folder  # before NiceGUI is loaded: not the toolbox's own .nicegui
        if sys.argv[1:2] == ["window"]:
            options = [option for option in sys.argv[2:] if option != "--no-open"]
            settings = None
            if "--toolbox" in options:
                at = options.index("--toolbox")
                if at + 1 >= len(options):
                    sys.exit("which settings folder? ... tested window --toolbox <settings folder>")
                settings = Path(options[at + 1]).resolve()
                del options[at:at + 2]
            show_window(int(options[0]) if options else WINDOW_PORT, "--no-open" not in sys.argv, settings)
        else:
            write_files(Path(folder), sys.argv[1:])
