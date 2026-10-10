import asyncio
import shlex
from pathlib import Path
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.files.file_types import ANY_FILE, FOLDER
from streamer_toolbox.core.data.box_value import to_bool, understand


class ProgramActions:
    """Runs a program on this PC (SAMMI's Run Command), e.g. a Python script that downloads a raid clip, and
    gives back what it printed. Flow only: the API and SAMMI can't start programs through it."""

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("system.run", self.run, "Runs a program, e.g. program = the .venv's python.exe, arguments = "
                    "the script and what it needs (a list, or text: put a part with spaces in \"quotes\"). Waits "
                    "until it's done (at most 'seconds') and gives back output (what it printed; JSON already "
                    "read), error_output and exit_code (0 = fine). wait off: just start it",
                    "Run program", group="Programs", flow_only=True,
                    outputs={"output": "any", "exit_code": "number", "error_output": "text"},
                    files={"program": ANY_FILE, "folder": FOLDER})

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


def _arguments(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if value is None or value == "":
        return []
    return [part[1:-1] if len(part) > 1 and part[0] == part[-1] == '"' else part
            for part in shlex.split(str(value), posix=False)]


def _text(data: bytes | None) -> str:
    return (data or b"").decode("utf-8", errors="replace")
