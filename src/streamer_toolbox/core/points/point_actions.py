from collections.abc import Callable

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.interfaces.point_bank import PointBank
from streamer_toolbox.core.points.boxes.add_points import AddPoints
from streamer_toolbox.core.points.boxes.get_points import GetPoints
from streamer_toolbox.core.points.boxes.give_points_to_a_viewer import GivePointsToAViewer
from streamer_toolbox.core.points.boxes.set_points import SetPoints
from streamer_toolbox.core.points.boxes.spend_points import SpendPoints
from streamer_toolbox.core.points.boxes.top_points import TopPoints


class PointActions:
    """The Points boxes: the toolbox's own currency per viewer, for flows (a command that costs points, a reward
    that gives some, a leaderboard). The viewer is usually Start's user_login, the platform Start's platform.
    `bank` gives where the points live right now (the toolbox's store or Mix It Up's currency): he can switch
    on the Points page without touching a flow.

    One Box class per box, in boxes/."""

    def __init__(self, bank: Callable[[], PointBank]) -> None:
        self._bank = bank

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (GetPoints(self._bank), AddPoints(self._bank), SetPoints(self._bank), SpendPoints(self._bank),
                    GivePointsToAViewer(self._bank), TopPoints(self._bank)):
            actions.add_box(box, "points")
