import json
import logging
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from streamer_toolbox.core.system.update_files import READY

log = logging.getLogger(__name__)
UPDATE_EXIT_CODE = 4  # the toolbox ends with this when a downloaded update waits (ToolboxLauncher → start())
EXE = "crazy-streamer-toolbox.exe"  # the Windows download's start program (WindowsLauncher)


class UpdateStarter:
    """In the launcher, after the toolbox stopped for an update: starts the swap (update_swap) with the new
    toolbox's Python, on its own, and the launcher ends, so nothing holds the old files any more. Gives False
    (the launcher then starts the old toolbox again) when no update is ready or its Python isn't there."""

    def __init__(self, folder: Path, root: Path, restart: list[str],
                 launch: Callable[..., object] = subprocess.Popen) -> None:
        self._folder = folder
        self._root = root
        self._restart = restart
        self._launch = launch

    def start(self) -> bool:
        ready = self._folder / READY
        try:
            data = json.loads(ready.read_text(encoding="utf-8"))
            new, version = Path(data["new"]), str(data["version"])
        except (OSError, ValueError, KeyError, TypeError):
            log.warning("the toolbox stopped for an update, but none is ready: starting it again")
            return False
        finally:
            ready.unlink(missing_ok=True)
        python = new / "python" / ("python.exe" if sys.platform == "win32" else "bin/python3")
        if not python.is_file():
            log.warning("the update has no Python in %s: starting the old toolbox again", new)
            return False
        command = [str(python), "-m", "streamer_toolbox.core.system.update_swap", "--new", str(new),
                   "--into", str(self._root), "--folder", str(self._folder), "--version", version,
                   "--", *self._restart]
        env = {**os.environ, "PYTHONPATH": str(new / "src")}
        if sys.platform == "win32":
            detached = {"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP}
        else:
            detached = {"start_new_session": True}
        with (self._folder / "swap.log").open("w", encoding="utf-8") as out:
            self._launch(command, cwd=new, stdout=out, stderr=out, stdin=subprocess.DEVNULL, env=env, **detached)
        log.info("updating to %s: the toolbox starts again by itself", version)
        return True

    @staticmethod
    def restart_command(root: Path, argv: list[str], window: bool) -> list[str]:
        """How the toolbox is started again after the swap: the Windows start program when it was opened in a
        window and the program is there (no console), else its Python with the same arguments as now."""
        exe = root / EXE
        if sys.platform == "win32" and window and exe.is_file():
            return [str(exe), *[a for a in argv if a not in ("--open", "window")]]
        return [sys.executable, "-m", "streamer_toolbox", *argv]

