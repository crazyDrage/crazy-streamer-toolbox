from typing import Any

from streamer_toolbox.connections.vtube_studio.boxes.vts_look_shared import Request
from streamer_toolbox.core.interfaces.box import Box


# what moves by itself (where the model is, how long it is loaded, an expression's seconds left) is left out, so
# two of them can be compared (Compare objects) to see what a "VTS model settings changed" was about (OPEN 91)
class GetModelSettings(Box):
    name = "get_model_settings"
    label = "Get model settings"
    help = "The loaded model's settings as one object: model, hotkeys, expressions, physics. Compare two with " \
           "Compare objects to see what changed"
    group = "Model"
    outputs = {"model": "text", "hotkeys": "object", "expressions": "object", "physics": "object"}

    def __init__(self, request: Request) -> None:
        self._request = request

    async def run(self) -> dict[str, Any]:
        model = await self._request("CurrentModelRequest")
        hotkeys = (await self._request("HotkeysInCurrentModelRequest")).get("availableHotkeys", [])
        expressions = (await self._request("ExpressionStateRequest", {"details": False})).get("expressions", [])
        physics = await self._request("GetCurrentModelPhysicsRequest")
        return {
            "model": model.get("modelName", ""),
            "model_id": model.get("modelID", ""),
            "parameters": model.get("numberOfLive2DParameters", 0),
            "parts": model.get("numberOfLive2DArtmeshes", 0),
            "textures": model.get("numberOfTextures", 0),
            "texture_size": model.get("textureResolution", 0),
            "has_physics_file": bool(model.get("hasPhysicsFile")),
            "hotkeys": _by_name(hotkeys, lambda h: {
                "action": h.get("type", ""), "file": h.get("file", ""),
                "keys": " + ".join(h.get("keyCombination", [])), "button": h.get("onScreenButtonID", -1)}),
            "expressions": _by_name(expressions, lambda e: {
                "file": e.get("file", ""), "on": bool(e.get("active")),
                "off_when_key_let_go": bool(e.get("deactivateWhenKeyIsLetGo")),
                "auto_off": bool(e.get("autoDeactivateAfterSeconds"))}),
            "physics": {
                "on": bool(physics.get("physicsSwitchedOn")), "fps": physics.get("physicsFPSSetting", 0),
                "strength": physics.get("baseStrength", 0), "wind": physics.get("baseWind", 0),
                "groups": _by_name(physics.get("physicsGroups", []), lambda g: {
                    "strength": g.get("strengthMultiplier", 1), "wind": g.get("windMultiplier", 1)},
                    name_key="groupName")},
        }


def _by_name(entries: list[dict[str, Any]], shape, name_key: str = "name") -> dict[str, Any]:
    """{name: shape(entry)}; a name that is there twice (or none) gets " 2", " 3" ... so nothing is lost."""
    named: dict[str, Any] = {}
    for entry in entries:
        name = str(entry.get(name_key) or "(no name)")
        key, number = name, 2
        while key in named:
            key, number = f"{name} {number}", number + 1
        named[key] = shape(entry)
    return named
