from typing import TYPE_CHECKING

from streamer_toolbox.connections.vtube_studio.vts_animation import VtsAnimation
from streamer_toolbox.core.data.box_value import to_bool
from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.vts_connection import VtsConnection


class PlayModelAnimation(Box):
    name = "play_animation"
    label = "Play model animation"
    help = "Plays a model animation: the model goes from spot to spot, each step taking its own time. The steps " \
           "are kept in this box (Edit: record them by moving the model in VTS); the box ends when the animation " \
           "is done. A new animation stops the one playing"
    group = "Model position"
    editors = {"animation": "vts_animation"}
    labels = {"back_to_start": "Back to the start", "back_seconds": "Seconds to go back"}
    hints = {"repeat": "Play it this many times in a row",
             "loop_forever": "Keeps playing in the background until a Stop model animation box (or another "
                             "animation) stops it. The flow goes on at once",
             "back_to_start": "At the end, go back to where the model was when it started"}

    def __init__(self, vts: "VtsConnection") -> None:
        self._vts = vts

    async def run(self, animation: dict, repeat: int = 1, loop_forever: bool = False, back_to_start: bool = False,
                  back_seconds: float = 1.0) -> None:
        await self._vts.play_animation(VtsAnimation.from_dict(animation), int(repeat), to_bool(back_to_start),
                                       float(back_seconds), to_bool(loop_forever))
