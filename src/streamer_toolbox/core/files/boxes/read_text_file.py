import asyncio
from pathlib import Path

from streamer_toolbox.core.files.file_types import ANY_FILE
from streamer_toolbox.core.interfaces.box import Box


class ReadTextFile(Box):
    name = "read_text"
    label = "Read text file"
    help = "Reads a text file; save it in a variable"
    group = "Text files"
    flow_only = True
    files = {"path": ANY_FILE}

    async def run(self, path: str) -> str:
        return (await asyncio.to_thread(Path(path).read_text, encoding="utf-8")).strip()
