from typing import Any

from streamer_toolbox.connections.obs.boxes.obs_scene_box import ObsSceneBox


class GetTransition(ObsSceneBox):
    name = "get_transition"
    label = "Get transition"
    help = "The transition scene switches use now and its length"
    outputs = {"transition": "text", "seconds": "number"}
    live = True
    group = "Scenes"

    async def run(self) -> dict[str, Any]:
        now = await self._requests("GetCurrentSceneTransition")
        duration = now.get("transitionDuration")
        return {"transition": now.get("transitionName", ""),
                "seconds": round(duration / 1000, 3) if isinstance(duration, (int, float)) else 0}
