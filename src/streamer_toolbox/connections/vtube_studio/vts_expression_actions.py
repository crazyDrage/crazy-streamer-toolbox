from streamer_toolbox.connections.vtube_studio.boxes.is_expression_on import IsExpressionOn
from streamer_toolbox.connections.vtube_studio.boxes.set_expression import SetExpression
from streamer_toolbox.connections.vtube_studio.boxes.vts_expression_box import Request
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class VtsExpressionActions:
    """VTube Studio boxes for the model's expressions (.exp3.json): switch one on or off, ask whether one is on.

    One Box class per box, in boxes/."""

    def __init__(self, request: Request) -> None:
        self._request = request

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (SetExpression(self._request), IsExpressionOn(self._request)):
            actions.add_box(box, "vts")
