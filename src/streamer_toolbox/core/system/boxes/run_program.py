import asyncio
from pathlib import Path
from typing import Any

from streamer_toolbox.core.data.box_value import to_bool, understand
from streamer_toolbox.core.files.file_types import ANY_FILE, FOLDER
from streamer_toolbox.core.interfaces.box import Box
from streamer_toolbox.core.system.boxes.program_shared import _arguments, _text


class RunProgram(Box):
    name = "run"
    label = "Run program"
    help = "Runs a program, e.g. program = the .venv's python.exe, arguments = the script and what it needs (a " \
           'list, or text: put a part with spaces in "quotes"). Waits until it\'s done (at most \'seconds\') and ' \
           "gives back output (what it printed; JSON already read), error_output and exit_code (0 = fine). wait " \
           "off: just start it"
    group = "Programs"
    flow_only = True
    outputs = {"output": "any", "exit_code": "number", "error_output": "text"}
    files = {"program": ANY_FILE, "folder": FOLDER}

    async def run(self, program: str, arguments: Any = "", folder: str = "", wait: bool = True,
                  seconds: float = 60.0, fail_on_error: bool = True) -> dict[str, Any]:
        args = _arguments(arguments)
        cwd = str(Path(folder)) if folder else None
        try:
            process = await asyncio.create_subprocess_exec(
                str(program), *args, cwd=cwd, stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE if to_bool(wait) else asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE if to_bool(wait) else asyncio.subprocess.DEVNULL)
        except OSError as e:
            raise FileNotFoundError(f"can't start {program!r}: {e}") from None
        if not to_bool(wait):
            return {"output": "", "error_output": "", "exit_code": None, "pid": process.pid}
        try:
            out, err = await asyncio.wait_for(process.communicate(), float(seconds))
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise TimeoutError(f"{Path(str(program)).name} didn't finish within {float(seconds):g} s (stopped)") \
                from None
        result = {"output": understand(_text(out).strip()), "error_output": _text(err).strip(),
                  "exit_code": process.returncode, "pid": process.pid}
        if process.returncode != 0 and to_bool(fail_on_error):
            raise RuntimeError(f"{Path(str(program)).name} ended with exit code {process.returncode}: "
                               f"{(result['error_output'] or str(result['output']))[-300:]}")
        return result
