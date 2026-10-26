from collections.abc import Awaitable, Callable
from typing import Any

Request = Callable[..., Awaitable[dict[str, Any]]]  # (message type, data) → VTS's answer data
CLICKED = "ModelClickedEvent"  # Record pin spot waits for one of these
PIN_SPOTS = {"center": "Center", "random": "Random"}  # where on the art mesh an item gets pinned
EXACT_SPOT, MODEL_PART = "exact spot", "model part"
PIN_TO = (EXACT_SPOT, MODEL_PART)  # the two ways to say where an item gets pinned
PIN_SHOWN = {"saved_spot": ("pin_to", (EXACT_SPOT,)), "art_mesh": ("pin_to", (MODEL_PART,)),
             "spot": ("pin_to", (MODEL_PART,))}  # the box form only shows the chosen way's fields
# what a pinned item's angle is counted from: as the item is now (the angle is added), the model (0 = upright
# on the model, however it is turned), the screen, or the spot itself (the same on the part however it bends)
ANGLE_FROM = {"item": "RelativeToCurrentItemRotation", "model": "RelativeToModel", "screen": "RelativeToWorld",
              "spot": "RelativeToPinPosition"}
PIN_LABELS = {"pin_to": "Pin to", "saved_spot": "Exact spot", "art_mesh": "Model part",
              "spot": "Where on that part", "angle_from": "Angle counted from"}
PIN_HINTS = {"pin_to": "exact spot: a spot you clicked on the model · model part: a part by name",
             "saved_spot": "Pick a variable (a new name is fine), press Save current below, then click "
                           "the spot on your model in VTube Studio. The spot stays in that variable",
             "art_mesh": "Empty = a random part",
             "angle_from": "model: 0 = upright on the model, however it is turned · screen: 0 = upright "
                           "on screen · spot: the same on that part however it bends · item: added to "
                           "the angle the item has"}


async def _pin_to() -> list[str]:
    return list(PIN_TO)


async def _pin_spots() -> list[str]:
    return list(PIN_SPOTS)


async def _angle_from() -> list[str]:
    return list(ANGLE_FROM)


def _pin_target(pin_to: str, saved_spot: dict[str, Any] | None, art_mesh: str, spot: str) -> tuple[str, dict]:
    """VTS's vertexPinType and pinInfo for the chosen way (PIN_TO)."""
    if pin_to not in PIN_TO:
        raise ValueError(f"pin_to must be one of {', '.join(PIN_TO)}, not {pin_to!r}")
    if pin_to == EXACT_SPOT:
        if not saved_spot:
            raise ValueError("no exact spot is set: pick its variable and press Save current, or set "
                             f"'Pin to' to {MODEL_PART}")
        return "Provided", _pin_info(saved_spot)
    if spot not in PIN_SPOTS:
        raise ValueError(f"spot must be one of {', '.join(PIN_SPOTS)}, not {spot!r}")
    return PIN_SPOTS[spot], {"modelID": "", "artMeshID": art_mesh, "angle": 0, "size": 0}


def _pin_info(spot: dict[str, Any]) -> dict[str, Any]:
    """A recorded spot as VTS's pinInfo ("Provided" pin type)."""
    try:
        vertices, weights = list(spot["vertices"]), [float(w) for w in spot["weights"]]
        return {"modelID": spot.get("model_id", ""), "artMeshID": spot["art_mesh"], "angle": 0, "size": 0,
                **{f"vertexID{i}": int(vertices[i - 1]) for i in (1, 2, 3)},
                **{f"vertexWeight{i}": weights[i - 1] for i in (1, 2, 3)}}
    except (KeyError, IndexError, TypeError, ValueError) as e:
        raise ValueError(f"saved_spot isn't a pin spot from Record pin spot ({e})") from e
