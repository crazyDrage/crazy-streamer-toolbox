"""Puts a downloaded toolbox in place of the one that just stopped, then starts it again (UpdateStarter runs this
with the NEW toolbox's Python, so the old python folder is free to be replaced):

    <new>/python/python.exe -m streamer_toolbox.core.system.update_swap --new <new> --into <root>
        --folder <update folder> --version 0.3.0 -- <the command that starts the toolbox again>

Keep these arguments in every version: an older toolbox starts the swap of the newer one with them."""
import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

from streamer_toolbox.core.system.update_files import RESULT
from streamer_toolbox.core.system.update_window import UpdateWindow

log = logging.getLogger(__name__)
REPLACED = ("src", "python")  # the toolbox's own: replaced whole, so no old file stays behind
KEPT = ("config", ".venv")  # never touched: his settings (when they are in the toolbox's folder), Linux's libraries


class UpdateSwap:
    """The new toolbox's files into the old one's folder. src/ and python/ are moved aside first (into `old`) and
    replaced whole; every other file of the download is copied over its old one (plugins he added stay);
    config/ is never touched. A file still in use (the start program closing) is tried again for a while. If
    anything fails, the old src/ and python/ go back, so the old version still starts."""

    def __init__(self, new: Path, into: Path, old: Path, tries: int = 120,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self._new = new
        self._into = into
        self._old = old
        self._tries = tries
        self._sleep = sleep

    def run(self) -> None:
        if not (self._new / "src" / "streamer_toolbox").is_dir():
            raise RuntimeError(f"no toolbox in {self._new}")
        shutil.rmtree(self._old, ignore_errors=True)
        self._old.mkdir(parents=True)
        moved = []
        try:
            for name in REPLACED:
                if (self._into / name).exists():
                    self._retry(lambda: (self._into / name).rename(self._old / name))
                    moved.append(name)
            for item in self._new.iterdir():
                if item.name in KEPT:
                    continue
                target = self._into / item.name
                if item.is_dir():
                    for file in sorted(f for f in item.rglob("*") if f.is_file()):
                        self._copy(file, target / file.relative_to(item))
                else:
                    self._copy(item, target)
        except Exception:
            for name in moved:
                shutil.rmtree(self._into / name, ignore_errors=True)
                (self._old / name).rename(self._into / name)
            raise

    def _copy(self, source: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        self._retry(lambda: shutil.copy2(source, target))

    def _retry(self, step: Callable[[], object]) -> None:
        for attempt in range(self._tries):
            try:
                step()
                return
            except PermissionError:  # Windows: a program that is closing still holds it
                if attempt == self._tries - 1:
                    raise
                self._sleep(0.5)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--new", type=Path, required=True)
    parser.add_argument("--into", type=Path, required=True)
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--version", default="")
    parser.add_argument("restart", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    restart = [part for part in args.restart if part != "--"]
    UpdateWindow(args.version).run(lambda: swap(args.new, args.into, args.folder, args.version, restart))


def swap(new: Path, into: Path, folder: Path, version: str, restart: list[str]) -> str:
    """The swap, its result for the toolbox, and the start of the toolbox again; what the update window says."""
    result = {"version": version, "ok": True, "error": ""}
    try:
        UpdateSwap(new, into, folder / "old").run()
        log.info("updated to %s", version)
    except Exception as e:
        log.exception("the update didn't work; the old version stays")
        result.update(ok=False, error=str(e) or type(e).__name__)
    (folder / RESULT).write_text(json.dumps(result), encoding="utf-8")
    if restart:
        start_again(restart, into)
    if result["ok"]:
        return f"Done. Version {version} is starting, its window opens in a moment."
    return ("The update didn't work, so the old version stays. It is starting again.\n"
            "What happened is in cache/update/swap.log in the settings folder.")


def start_again(command: list[str], root: Path) -> None:
    """Starts the toolbox again, on its own (this swap ends right after): with a console window of its own
    on Windows, as the start script had (the start program needs none)."""
    env = {**os.environ, "PYTHONPATH": str(root / "src")}
    if sys.platform == "win32":
        flags = 0 if command[0].endswith(".exe") and "python" not in Path(command[0]).name else \
            subprocess.CREATE_NEW_CONSOLE
        subprocess.Popen(command, cwd=root, env=env, creationflags=flags)
    else:
        subprocess.Popen(command, cwd=root, env=env, start_new_session=True)


if __name__ == "__main__":
    main()
