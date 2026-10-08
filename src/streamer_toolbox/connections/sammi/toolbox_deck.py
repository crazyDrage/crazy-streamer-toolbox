import json

from streamer_toolbox.core.actions.action_description import describe_action
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.api.caller import Caller
from streamer_toolbox.connections.sammi.sammi_deck_builder import SammiDeckBuilder


def toolbox_deck(actions: ActionRegistry, callers: tuple[Caller, ...], port: int) -> tuple[str, int]:
    """The SAMMI deck JSON with one button per action the local (tokenless) caller may run, and the button count."""
    caller = next((c for c in callers if c.local), None)
    allowed = [describe_action(a) for a in actions.all() if caller is None or caller.may_run(a.name)]
    deck = SammiDeckBuilder(f"http://127.0.0.1:{port}").build(allowed)
    return json.dumps(deck, indent=1), len(allowed)
