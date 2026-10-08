from typing import Any

from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class ObsSceneActions:
    """OBS boxes for scenes and transitions: which transition a scene switch uses (and how long it takes), and
    what is in a scene (each source, shown or not), e.g. to hide everything in a For each."""

    def __init__(self, requests: ObsRequests) -> None:
        self._requests = requests

    def add_to(self, actions: ActionRegistry) -> None:
        scenes = {"group": "Scenes"}
        actions.add("obs.set_transition", self.set_transition, "Picks the transition scene switches use (Fade, "
                    "Cut, a stinger, ...) and how long it takes", "Set transition",
                    options={"transition": self.transition_names},
                    hints={"seconds": "empty = as it is (a Cut or a stinger has its own length)"}, **scenes)
        actions.add("obs.get_transition", self.get_transition, "The transition scene switches use now and its "
                    "length", "Get transition", outputs={"transition": "text", "seconds": "number"}, live=True,
                    **scenes)
        actions.add("obs.get_scene_sources", self.scene_sources, "What is in a scene, top first: a list of "
                    "{source, visible, kind}", "Scene sources", options={"scene": self._requests.scene_names},
                    **scenes)

    async def transition_names(self) -> list[str]:
        return [t["transitionName"] for t in (await self._requests("GetSceneTransitionList"))["transitions"]]

    async def set_transition(self, transition: str, seconds: Any = "") -> None:
        milliseconds = round(float(seconds) * 1000) if str(seconds).strip() != "" else None
        if milliseconds is not None and not 50 <= milliseconds <= 20000:  # checked first: nothing half done
            raise ValueError(f"OBS takes 0.05 to 20 seconds for a transition, not {seconds}")
        await self._requests("SetCurrentSceneTransition", {"transitionName": transition})
        if milliseconds is not None:
            await self._requests("SetCurrentSceneTransitionDuration", {"transitionDuration": milliseconds})

    async def get_transition(self) -> dict[str, Any]:
        now = await self._requests("GetCurrentSceneTransition")
        duration = now.get("transitionDuration")
        return {"transition": now.get("transitionName", ""),
                "seconds": round(duration / 1000, 3) if isinstance(duration, (int, float)) else 0}

    async def scene_sources(self, scene: str) -> list[dict[str, Any]]:
        items = (await self._requests("GetSceneItemList", {"sceneName": scene}))["sceneItems"]
        ordered = sorted(items, key=lambda i: i.get("sceneItemIndex", 0), reverse=True)  # OBS: 0 = bottom
        return [{"source": i["sourceName"], "visible": bool(i.get("sceneItemEnabled")),
                 "kind": i.get("inputKind") or ("group" if i.get("isGroup") else "scene")}
                for i in ordered]
