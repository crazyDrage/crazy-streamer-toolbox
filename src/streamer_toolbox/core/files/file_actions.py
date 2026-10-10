import asyncio
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.box_value import to_bool
from streamer_toolbox.core.files.file_types import ANY_FILE


class FileActions:
    """Text file boxes, e.g. a counter an OBS text source shows (SAMMI's lizard_combo.txt). Flow only: they're
    not offered over the API or in the SAMMI deck, so no caller can write files on this PC."""

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("file.write_text", self.write_text, "Writes text into a file (makes the folder if needed); "
                    "append adds a line at the end instead", "Write text file", group="Text files",
                    flow_only=True, files={"path": ANY_FILE})
        actions.add("file.read_text", self.read_text, "Reads a text file; save it in a variable", "Read text file",
                    group="Text files", flow_only=True, files={"path": ANY_FILE})

    @staticmethod
    async def write_text(path: str, text: str = "", append: bool = False) -> None:
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

    @staticmethod
    async def read_text(path: str) -> str:
        return (await asyncio.to_thread(Path(path).read_text, encoding="utf-8")).strip()
