from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.system.boxes.run_program import RunProgram
from streamer_toolbox.core.system.boxes.run_python import RunPython


class ProgramActions:
    """Runs a program on this PC (SAMMI's Run Command), e.g. a Python script that downloads a raid clip, and
    gives back what it printed; and runs a function of a Python file (Run Python, its files in `python_folder`).
    Flow only: the API and SAMMI can't start programs through them.

    One Box class per box, in boxes/."""

    def __init__(self, python_folder: Path) -> None:
        self._python_folder = python_folder

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (RunProgram(), RunPython(self._python_folder)):
            actions.add_box(box, "system")
