import asyncio
import re
from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.box_value import to_bool

Request = Callable[..., Awaitable[dict[str, Any]]]  # (message type, data) → VTS's answer data
COLORS = {"red": "FF3030", "orange": "FF9900", "yellow": "FFE040", "green": "40D040", "blue": "4080FF",
          "purple": "A050FF", "pink": "FF80C0", "gray": "909090", "black": "202020", "white": "FFFFFF"}
PHYSICS_REPEAT = 4.0  # VTS keeps a physics override up to 5 s: it is sent again before that
PARAMETER_REPEAT = 0.5  # and a fed-in parameter is "lost" after 1 s without data


class VtsLookActions:
    """VTube Studio boxes for how the model looks, from its plugin API (github.com/DenchiSoft/VTubeStudio):
    tint the model or parts of it, physics strength / wind for a while, hold a tracking parameter
    (e.g. MouthOpen) at a value for a while, read one, the visual effects (VFX: a preset, on / off, one setting,
    random), whether the tracker sees your face, VTS's stats.

    Tints stay until reset (or until the toolbox disconnects: VTS resets them then). Physics and parameters only
    hold while they're sent again and again, so those boxes run for their seconds."""

    def __init__(self, request: Request) -> None:
        self._request = request
        self._lit = ""  # the part the picker's window shows lit up now (light_part)

    def add_to(self, actions: ActionRegistry) -> None:
        look = {"group": "Look"}
        actions.add("vts.tint", self.tint, "Tints the model, or the parts whose name has one of the words (darker "
                    "only: white = as it was)", "Tint model",
                    options={"color": _color_names}, colors=("color",), many={"picked": self.part_names},
                    lights={"picked": self.light_part},
                    labels={"parts": "Parts by word", "picked": "Picked parts"},
                    hints={"color": "a name (red, orange, ...), the colour picker, or hex like FF8800 / "
                                    "#FF880080 (with alpha)",
                           "parts": "words like hair, eye: any part whose name has one. Both parts fields "
                                    "empty = the whole model",
                           "picked": "exact parts of the loaded model, ticked in the list (the button)",
                           "lighting": "1 = your colour wins over VTS's scene lighting, 0 = the lighting wins"},
                    outputs={"parts_tinted": "number"}, **look)
        actions.add("vts.reset_tint", self.reset_tint, "Takes the tint away again (whole model or parts)",
                    "Reset tint", many={"picked": self.part_names}, lights={"picked": self.light_part},
                    labels={"parts": "Parts by word", "picked": "Picked parts"},
                    hints={"parts": "both parts fields empty = the whole model",
                           "picked": "exact parts of the loaded model, ticked in the list (the button)"}, **look)
        actions.add("vts.physics", self.physics, "Physics strength and / or wind (0 to 100) for some seconds; then "
                    "back to your own settings", "Physics / wind",
                    hints={"strength": "0 to 100, empty = as it is", "wind": "0 to 100, empty = as it is",
                           "seconds": "how long; the box waits that long"}, **look)
        params = {"group": "Parameters", "options": {"parameter": self.parameter_names}}
        actions.add("vts.hold_parameter", self.hold_parameter, "Holds a tracking parameter (e.g. MouthOpen, "
                    "FaceAngleX) at a value for some seconds, over what the tracking says", "Hold parameter",
                    hints={"seconds": "how long; the box waits that long",
                           "weight": "0 to 1: how much of the value is used (1 = all)"}, **params)
        actions.add("vts.get_parameter", self.get_parameter, "A tracking parameter's value now (and its range)",
                    "Get parameter", outputs={"value": "number", "min": "number", "max": "number"}, **params)
        vfx = {"group": "Visual effects"}
        actions.add("vts.effects_preset", self.effects_preset, "Loads a visual effects (VFX) preset you saved in "
                    "VTube Studio, fading over 'fade' seconds", "Effects preset",
                    options={"preset": self.preset_names}, hints={"fade": "0 to 2 seconds"}, **vfx)
        actions.add("vts.effects_on", self.effects_on, "Switches VTube Studio's visual effects on or off (what "
                    "they are set to stays)", "Effects on / off", options={"state": _states}, **vfx)
        actions.add("vts.set_effect", self.set_effect, "Sets one visual effect setting (e.g. Bloom_Strength 0.8; "
                    "a *_Strength above 0 turns that effect on)", "Set effect value",
                    options={"setting": self.effect_settings},
                    labels={"only_this": "Others back to default"},
                    hints={"value": "a number, true / false, or a colour like FF0000FF, as the setting needs",
                           "fade": "0 to 2 seconds", "only_this": "on: every other effect fades off"}, **vfx)
        actions.add("vts.random_effects", self.random_effects, "Random visual effects, for fun: chaos 0 = mild, "
                    "1 = complete chaos (0.4 to 0.5 looks good)", "Random effects", **vfx)
        model = {"group": "Model"}
        actions.add("vts.face_found", self.face_found, "Whether the tracker sees your face now (true / false)",
                    "Is face found", live=True, **model)
        actions.add("vts.get_stats", self.stats, "VTube Studio's numbers: FPS, version, minutes running, plugins",
                    "VTS stats", live=True, outputs={"fps": "number", "version": "text", "minutes": "number",
                                                     "plugins": "number"}, **model)

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


def rgba(color: Any) -> tuple[int, int, int, int]:
    """A colour name or hex (RRGGBB / RRGGBBAA, # optional) → 0-255 values."""
    text = str(color).strip().lstrip("#")
    text = COLORS.get(text.casefold(), text)
    if len(text) == 6:
        text += "FF"
    try:
        if len(text) != 8:
            raise ValueError
        return tuple(int(text[i:i + 2], 16) for i in range(0, 8, 2))  # type: ignore[return-value]
    except ValueError:
        raise ValueError(f"a colour is a name ({', '.join(COLORS)}) or hex like FF8800, not {color!r}") from None


def _matcher(parts: Any, picked: Any = "") -> dict[str, Any]:
    """Which parts VTS tints: those whose name has one of the words, and the picked ones by their exact name
    (a word would also catch ArtMesh12 for ArtMesh1); neither = the whole model."""
    words = [w.strip() for w in str(parts or "").replace(",", " ").split() if w.strip()]
    names = [n.strip() for n in str(picked or "").split(",") if n.strip()]
    if not words and not names:
        return {"tintAll": True}
    return {"tintAll": False} | ({"nameContains": words} if words else {}) | ({"nameExact": names} if names else {})


def _by_number(name: str) -> list[tuple[int, int | str]]:
    """A sort key that reads the digits in a name as numbers."""
    return [(0, int(piece)) if piece.isdigit() else (1, piece.casefold())
            for piece in re.split(r"(\d+)", name) if piece]


def _fade(fade: Any) -> float:
    return min(max(float(fade), 0.0), 2.0)


async def _color_names() -> list[str]:
    return list(COLORS)


async def _states() -> list[str]:
    return ["on", "off", "toggle"]
