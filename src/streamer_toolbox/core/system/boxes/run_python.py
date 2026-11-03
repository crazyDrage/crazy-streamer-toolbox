import asyncio
import inspect
import json
import logging
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from streamer_toolbox.core.actions.output_names import names_in
from streamer_toolbox.core.files.file_types import ANY_FILE
from streamer_toolbox.core.interfaces.box import Box
from streamer_toolbox.core.system.boxes.program_shared import _text
from streamer_toolbox.core.system.python_runner import RESULT
from streamer_toolbox.core.system.python_template import python_template

RUNNER = Path(__file__).parent.parent / "python_runner.py"
log = logging.getLogger(__name__)


class RunPython(Box):
    """His idea of 10-30: a box that runs a function of a Python file, with inputs and outputs he names. Each
    run starts a Python of its own (python_runner.py), so a file that hangs or breaks can't take the toolbox
    with it, and a changed file counts at the next run without a restart. Flow only: the API and SAMMI can't
    run code on his PC through it."""

    name = "python"
    label = "Run Python"
    help = "Runs one function of a Python file and gives what it returns. + Add value for each input: the " \
           "function gets them by name. Outputs: the names it gives back, each a dot. A file that isn't there " \
           "yet is made from a template first"
    group = "Programs"
    flow_only = True
    named_lines = True
    output_names = "outputs"
    outputs = {"printed": "text"}
    files = {"file": (".py",), "python": ANY_FILE}
    editors = {"file": "python_code"}  # the name or path, and Edit code: the file in a code window
    hints = {"file": "A name (e.g. lizard: kept in the toolbox's config/boxes/python/) or a .py file anywhere",
             "function": "The function it calls, run unless you changed it in the file",
             "outputs": "Names, separated by commas, e.g. text, count",
             "python": "Empty: the toolbox's own Python. Or a python.exe, e.g. a .venv's, for its libraries",
             "seconds": "The longest it may take; then it is stopped"}

    def __init__(self, folder: Path) -> None:
        self._folder = folder

    async def run(self, file: str, function: str = "run", outputs: str = "", python: str = "",
                  seconds: float = 30.0, **inputs: Any) -> dict[str, Any]:
        if not function.isidentifier():
            raise ValueError(f"function {function!r} can't be a Python function's name")
        names = names_in(outputs)
        path = self.path(file)
        if not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self.template({"function": function, "outputs": outputs, **inputs}), encoding="utf-8")
            log.info("Run Python: made %s from the template", path)
        program = Path(python) if python else Path(sys.executable)
        if not program.is_file():
            raise FileNotFoundError(f"no Python at {program}")
        out, err, code = await self._start(program, path, function, inputs, float(seconds))
        printed, _, answer = out.rpartition(RESULT)
        if code != 0 or not _:
            raise RuntimeError(f"{path.name}: {(err.strip() or out.strip() or f'exit code {code}')[-500:]}")
        given = json.loads(answer)
        result = given if isinstance(given, dict) else {"value": given}
        missing = [name for name in names if name not in result]
        if missing:
            log.warning("Run Python: %s gave no %s", path.name, ", ".join(missing))
        return {**{name: None for name in missing}, **result, "printed": printed.strip()}

    @staticmethod
    def template(params: Mapping[str, Any]) -> str:
        """A new file's text for a box with these values: its function, its inputs (the lines he named) as
        parameters and its outputs in the return."""
        own = {name for name in inspect.signature(RunPython.run).parameters if name not in ("self", "inputs")}
        function = params.get("function") or "run"
        return python_template(str(function), [name for name in params if name not in own],
                               names_in(params.get("outputs", "")))

    def path(self, file: str) -> Path:
        """A name or a path inside the box's folder (lizard, tools/lizard.py) → there, with .py; any other
        path stays as it is."""
        if not str(file).strip():
            raise ValueError("file: give it a name (e.g. lizard) or a .py file")
        path = Path(str(file).strip()).expanduser()
        if path.is_absolute():
            return path
        inside = (self._folder / path).with_suffix(".py").resolve()
        if not inside.is_relative_to(self._folder.resolve()):
            raise ValueError(f"file {file!r}: a name stays inside {self._folder}; give a full path for others")
        return inside

    @staticmethod
    async def _start(program: Path, path: Path, function: str, inputs: dict[str, Any],
                     seconds: float) -> tuple[str, str, int]:
        environment = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        try:
            process = await asyncio.create_subprocess_exec(
                str(program), str(RUNNER), str(path), function, cwd=str(path.parent), env=environment,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        except OSError as e:
            raise FileNotFoundError(f"can't start {program}: {e}") from None
        data = json.dumps(inputs, ensure_ascii=False, default=str).encode("utf-8")
        try:
            out, err = await asyncio.wait_for(process.communicate(data), seconds)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise TimeoutError(f"{path.name} didn't finish within {seconds:g} s (stopped)") from None
        return _text(out), _text(err), process.returncode
