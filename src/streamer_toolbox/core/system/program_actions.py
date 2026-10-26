from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.system.boxes.run_program import RunProgram


class ProgramActions:
    """Runs a program on this PC (SAMMI's Run Command), e.g. a Python script that downloads a raid clip, and
    gives back what it printed. Flow only: the API and SAMMI can't start programs through it.

    One Box class per box, in boxes/."""

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (RunProgram(),):
            actions.add_box(box, "system")
