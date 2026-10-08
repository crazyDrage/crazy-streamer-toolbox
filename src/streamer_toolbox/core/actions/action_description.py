import inspect
from typing import Any

from streamer_toolbox.core.actions.registered_action import RegisteredAction


def describe_action(action: RegisteredAction) -> dict[str, Any]:
    """The public view of an action, as GET /actions and the SAMMI deck use it."""
    return {"name": action.name, "label": action.title, "description": action.description,
            "params": required_and_optional_params(action)}


def required_and_optional_params(action: RegisteredAction) -> list[dict[str, Any]]:
    return [{"name": p.name, "required": p.default is inspect.Parameter.empty}
            for p in inspect.signature(action.handler).parameters.values()
            if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)]
