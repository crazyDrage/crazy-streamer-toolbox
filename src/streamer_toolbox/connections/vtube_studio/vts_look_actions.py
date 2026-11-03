import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.connections.vtube_studio.boxes.effects_on_off import EffectsOnOff
from streamer_toolbox.connections.vtube_studio.boxes.effects_preset import EffectsPreset
from streamer_toolbox.connections.vtube_studio.boxes.get_model_settings import GetModelSettings
from streamer_toolbox.connections.vtube_studio.boxes.get_parameter import GetParameter
from streamer_toolbox.connections.vtube_studio.boxes.hold_parameter import HoldParameter
from streamer_toolbox.connections.vtube_studio.boxes.is_face_found import IsFaceFound
from streamer_toolbox.connections.vtube_studio.boxes.physics_wind import PhysicsWind
from streamer_toolbox.connections.vtube_studio.boxes.random_effects import RandomEffects
from streamer_toolbox.connections.vtube_studio.boxes.reset_tint import ResetTint
from streamer_toolbox.connections.vtube_studio.boxes.set_effect_value import SetEffectValue
from streamer_toolbox.connections.vtube_studio.boxes.tint_model import TintModel
from streamer_toolbox.connections.vtube_studio.boxes.vts_look_shared import (PARAMETER_REPEAT, PHYSICS_REPEAT,
                                                                             Request, _by_number, _fade, _matcher,
                                                                             rgba)
from streamer_toolbox.connections.vtube_studio.boxes.vts_stats import VtsStats
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.box_value import to_bool


class VtsLookActions:
    """VTube Studio boxes for how the model looks, from its plugin API (github.com/DenchiSoft/VTubeStudio):
    tint the model or parts of it, physics strength / wind for a while, hold a tracking parameter
    (e.g. MouthOpen) at a value for a while, read one, the visual effects (VFX: a preset, on / off, one setting,
    random), whether the tracker sees your face, VTS's stats, the model's settings as one object.

    Tints stay until reset (or until the toolbox disconnects: VTS resets them then). Physics and parameters only
    hold while they're sent again and again, so those boxes run for their seconds."""

    def __init__(self, request: Request) -> None:
        self._request = request
        self._lit = ""  # the part the picker's window shows lit up now (light_part)

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (TintModel(self), ResetTint(self), PhysicsWind(self), HoldParameter(self), GetParameter(self),
                    EffectsPreset(self), EffectsOnOff(self), SetEffectValue(self), RandomEffects(self),
                    IsFaceFound(self), VtsStats(self), GetModelSettings(self._request)):
            actions.add_box(box, "vts")

    # ---- tint ----

    async def part_names(self) -> list[str]:
        """The parts (ArtMeshes) of the model that is loaded now, numbers in order (ArtMesh6 before ArtMesh10)."""
        return sorted((await self._request("ArtMeshListRequest")).get("artMeshNames", []), key=_by_number)

    async def light_part(self, part: str, color: str = "FF00FF") -> None:
        """Shows one part in `color` on the model, for the Picked parts window (the name under the mouse);
        the part lit before goes back to untinted, "" = none is lit. A tint a flow gave that part is gone
        after it: VTS can't tell what a part's tint was."""
        before, self._lit = self._lit, ""
        if before and before != part:
            await self._tint_exact("FFFFFF", before)
        if part:
            await self._tint_exact(color, part)
            self._lit = part

    async def _tint_exact(self, color: str, part: str) -> None:
        r, g, b, a = rgba(color)
        await self._request("ColorTintRequest", {
            "colorTint": {"colorR": r, "colorG": g, "colorB": b, "colorA": a, "mixWithSceneLightingColor": 1.0},
            "artMeshMatcher": {"tintAll": False, "nameExact": [part]}})

    async def tint(self, color: str = "red", parts: str = "", picked: str = "",
                   lighting: float = 1.0) -> dict[str, int]:
        r, g, b, a = rgba(color)
        tint = {"colorR": r, "colorG": g, "colorB": b, "colorA": a,
                "mixWithSceneLightingColor": min(max(float(lighting), 0.0), 1.0)}
        answer = await self._request("ColorTintRequest", {"colorTint": tint,
                                                               "artMeshMatcher": _matcher(parts, picked)})
        return {"parts_tinted": answer.get("matchedArtMeshes", 0)}

    async def reset_tint(self, parts: str = "", picked: str = "") -> None:
        await self.tint("FFFFFF", parts, picked)

    # ---- physics ----

    async def physics(self, strength: Any = "", wind: Any = "", seconds: float = 5.0) -> None:
        overrides = {}
        for key, value in (("strengthOverrides", strength), ("windOverrides", wind)):
            if str(value).strip() != "":
                overrides[key] = [{"id": "", "value": round(min(max(float(value), 0), 100)), "setBaseValue": True}]
        if not overrides:
            raise ValueError("set strength or wind (0 to 100)")
        await self._repeat(float(seconds), PHYSICS_REPEAT, lambda left: self._request(
            "SetCurrentModelPhysicsRequest", {key: [dict(o, overrideSeconds=min(max(left, 0.5), 5.0))
                                                    for o in items] for key, items in overrides.items()}))

    # ---- parameters ----

    async def parameter_names(self) -> list[str]:
        answer = await self._request("InputParameterListRequest")
        return [p["name"] for p in answer.get("defaultParameters", []) + answer.get("customParameters", [])]

    async def hold_parameter(self, parameter: str, value: float, seconds: float = 2.0, weight: float = 1.0) -> None:
        data = {"faceFound": False, "mode": "set", "parameterValues": [
            {"id": parameter, "value": float(value), "weight": min(max(float(weight), 0.0), 1.0)}]}
        await self._repeat(float(seconds), PARAMETER_REPEAT, lambda _: self._request("InjectParameterDataRequest",
                                                                                      data))

    async def get_parameter(self, parameter: str) -> dict[str, float]:
        answer = await self._request("ParameterValueRequest", {"name": parameter})
        return {"value": answer.get("value", 0), "min": answer.get("min", 0), "max": answer.get("max", 0)}

    # ---- visual effects ----

    async def preset_names(self) -> list[str]:
        answer = await self._request("PostProcessingListRequest", {
            "fillPostProcessingPresetsArray": True, "fillPostProcessingEffectsArray": False})
        return answer.get("postProcessingPresets", [])

    async def effect_settings(self) -> dict[str, dict[str, str]]:
        """effect → {setting id: "setting id · what it does"}: the field gets an effect picker first."""
        answer = await self._request("PostProcessingListRequest", {
            "fillPostProcessingPresetsArray": False, "fillPostProcessingEffectsArray": True})
        return {effect.get("explanation") or effect["enumID"]: {
                    c["enumID"]: f"{c['enumID']} · {c.get('explanation', '')}".rstrip(" ·")
                    for c in effect.get("configEntries", [])}
                for effect in answer.get("postProcessingEffects", [])}

    async def effects_preset(self, preset: str, fade: float = 1.0) -> None:
        await self._effects(setPostProcessingPreset=True, presetToSet=str(preset), postProcessingFadeTime=_fade(fade))

    async def effects_on(self, state: str = "on") -> bool:
        if state == "toggle":
            now = await self._request("PostProcessingListRequest", {
                "fillPostProcessingPresetsArray": False, "fillPostProcessingEffectsArray": False})
            on = not now.get("postProcessingActive", False)
        else:
            on = state != "off" and to_bool(state)
        await self._effects(postProcessingOn=on)
        return on

    async def set_effect(self, setting: str, value: Any, fade: float = 0.5, only_this: bool = False) -> None:
        text = str(value).lower() if isinstance(value, bool) else str(value).lstrip("#")
        await self._effects(setPostProcessingValues=True, postProcessingFadeTime=_fade(fade),
                            setAllOtherValuesToDefault=to_bool(only_this),
                            postProcessingValues=[{"configID": str(setting), "configValue": text}])

    async def random_effects(self, chaos: float = 0.45) -> None:
        await self._effects(randomizeAll=True, randomizeAllChaosLevel=min(max(float(chaos), 0.0), 1.0))

    async def _effects(self, **changes: Any) -> dict[str, Any]:
        """A PostProcessingUpdateRequest that keeps the effects on unless told otherwise."""
        data = {"postProcessingOn": True, "setPostProcessingPreset": False, "setPostProcessingValues": False,
                "presetToSet": "", "postProcessingFadeTime": 0.0, "setAllOtherValuesToDefault": False,
                "usingRestrictedEffects": False, "randomizeAll": False, "randomizeAllChaosLevel": 0.0,
                "postProcessingValues": [], **changes}
        return await self._request("PostProcessingUpdateRequest", data)

    # ---- model ----

    async def face_found(self) -> bool:
        return bool((await self._request("FaceFoundRequest")).get("found"))

    async def stats(self) -> dict[str, Any]:
        s = await self._request("StatisticsRequest")
        return {"fps": s.get("framerate", 0), "version": s.get("vTubeStudioVersion", ""),
                "minutes": round(s.get("uptime", 0) / 60000), "plugins": s.get("connectedPlugins", 0)}

    async def _repeat(self, seconds: float, every: float, send: Callable[[float], Awaitable[Any]]) -> None:
        """send(seconds left) now and every `every` seconds until `seconds` are over."""
        loop = asyncio.get_running_loop()
        end = loop.time() + max(seconds, 0.0)
        while True:
            left = end - loop.time()
            await send(left)
            if left <= every:
                await asyncio.sleep(max(left, 0.0))
                return
            await asyncio.sleep(every)


