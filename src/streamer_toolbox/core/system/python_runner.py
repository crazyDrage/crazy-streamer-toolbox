"""Runs one function of a Python file for the Run Python box. Not imported by the toolbox: the box starts it as

    <python> python_runner.py <file> <function>

with the box's inputs as a JSON object on stdin. The function gets them by name; what it gives back is written
to stdout as JSON after the line RESULT, so whatever the file prints before stays apart from it. An error
goes to stderr and ends it with exit code 1.

It runs on whatever Python the box is set to (a project's .venv too), so it uses nothing but the standard
library and nothing newer than Python 3.8. The file is loaded under its own name, not as __main__: its
`if __name__ == "__main__":` part doesn't run, so the same file can still be started by hand."""
import asyncio
import importlib.util
import inspect
import json
import sys
from pathlib import Path

RESULT = "\x00streamer-toolbox result\x00"


def main() -> int:
    file, function = Path(sys.argv[1]), sys.argv[2]
    inputs = json.loads(sys.stdin.read() or "{}")
    sys.path.insert(0, str(file.parent))  # its own imports next to it (the embedded Windows Python adds nothing)
    spec = importlib.util.spec_from_file_location(file.stem, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    called = getattr(module, function, None)
    if not callable(called):
        print(f"{file.name} has no function {function}()", file=sys.stderr)
        return 1
    result = called(**inputs)
    if inspect.isawaitable(result):
        result = asyncio.run(_wait(result))
    sys.stdout.write("\n" + RESULT + json.dumps(result, ensure_ascii=False, default=str) + "\n")
    return 0


async def _wait(awaitable):
    return await awaitable


if __name__ == "__main__":
    sys.exit(main())
