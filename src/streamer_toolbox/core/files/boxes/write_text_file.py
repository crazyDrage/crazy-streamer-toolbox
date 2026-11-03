import asyncio
from pathlib import Path

from streamer_toolbox.core.data.box_value import to_bool
from streamer_toolbox.core.files.file_types import ANY_FILE
from streamer_toolbox.core.interfaces.box import Box


class WriteTextFile(Box):
    name = "write_text"
    label = "Write text file"
    help = "Writes text into a file (makes the folder if needed); append adds a line at the end instead"
    group = "Text files"
    flow_only = True
    files = {"path": ANY_FILE}

    async def run(self, path: str, text: str = "", append: bool = False) -> None:
        def write() -> None:
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            if to_bool(append):
                # a line of its own, also after a file that was written whole (no line break at its end)
                before = target.read_text(encoding="utf-8") if target.exists() else ""
                with target.open("a", encoding="utf-8") as out:
                    out.write(f"{text}\n" if before.endswith("\n") or not before else f"\n{text}\n")
            else:
                target.write_text(str(text), encoding="utf-8")

        await asyncio.to_thread(write)
