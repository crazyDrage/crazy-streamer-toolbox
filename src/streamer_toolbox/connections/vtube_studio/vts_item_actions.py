import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry

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


class VtsItemActions:
    """VTube Studio boxes for items (pictures from VTS's Items folder): put one into the scene, move it, take it
    out, pin it onto the model (on an exact spot recorded by a click on the model, or on a model part), and
    whether one is in the scene. The connection hands it the clicks VTS reports (clicked)."""

    def __init__(self, request: Request) -> None:
        self._request = request
        self._click: asyncio.Future | None = None  # Record pin spot waits on it

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("vts.load_item", self.load_item, "Puts an item (a file from VTS's Items folder) into the "
                    "scene; x/y from -1 to 1 like the model. Returns its instance id", "Load item", group="Items",
                    options={"file": self.item_files})
        actions.add("vts.remove_items", self.remove_items, "Removes an item by instance id (from Load item), or "
                    "all items the toolbox loaded when left empty", "Remove items", group="Items")
        actions.add("vts.move_item", self.move_item, "Moves a loaded item (instance id from Load item) over "
                    "some seconds; size / rotation -1000 keep them", "Move item", group="Items")
        pin_labels = {"pin_to": "Pin to", "saved_spot": "Exact spot", "art_mesh": "Model part",
                      "spot": "Where on that part", "angle_from": "Angle counted from"}
        pin_hints = {"pin_to": "exact spot: a spot you clicked on the model · model part: a part by name",
                     "saved_spot": "Pick a variable (a new name is fine), press Save current below, then click "
                                   "the spot on your model in VTube Studio. The spot stays in that variable",
                     "art_mesh": "Empty = a random part",
                     "angle_from": "model: 0 = upright on the model, however it is turned · screen: 0 = upright "
                                   "on screen · spot: the same on that part however it bends · item: added to "
                                   "the angle the item has"}
        actions.add("vts.add_pinned_item", self.add_pinned_item, "Puts an item (a file from VTS's Items folder) "
                    "onto the model in one step: loads it and pins its middle on the exact spot (or on a model "
                    "part). Gives its instance id, for Remove items / Unpin item", "Add item pinned to model",
                    group="Items", options={"file": self.item_files, "pin_to": _pin_to,
                                            "art_mesh": self.art_mesh_names,
                                            "spot": _pin_spots, "angle_from": _angle_from},
                    capture="vts.record_pin_spot:saved_spot", outputs={"instance": "text", "pinned": "yes/no"},
                    shown=PIN_SHOWN,
                    labels={**pin_labels, "seconds": "Fade in (s)"},
                    hints={**pin_hints, "size": "0 to 1, like Load item", "angle": "degrees",
                           "order": "higher = in front of other items"})
        actions.add("vts.pin_item", self.pin_item, "Pins a loaded item onto the model: its middle goes on an "
                    "exact spot (Save current: click the model in VTS), or on a model part (its center or a "
                    "random spot). Angle and size empty = it keeps the ones it has", "Pin item to model",
                    group="Items",
                    options={"pin_to": _pin_to, "art_mesh": self.art_mesh_names, "spot": _pin_spots,
                             "angle_from": _angle_from},
                    capture="vts.record_pin_spot:saved_spot", shown=PIN_SHOWN,
                    labels={**pin_labels, "instance": "Item"},
                    hints={**pin_hints, "instance": "The instance id Load item gives: wire it from that box "
                                                    "(Wire from a box)",
                           "angle": "degrees; empty = keep the item's angle",
                           "size": "0 to 1; empty = keep the item's size"})
        actions.add("vts.record_pin_spot", self.record_pin_spot, "Waits for you to click the model in VTube "
                    "Studio (up to 'seconds') and gives back that exact spot, for Pin item's saved_spot. Save it in a "
                    "variable", "Record pin spot", group="Items",
                    outputs={"art_mesh": "text", "model": "text"})
        actions.add("vts.unpin_item", self.unpin_item, "Unpins an item from the model; it stays where it is",
                    "Unpin item", group="Items")
        actions.add("vts.item_in_scene", self.item_in_scene, "Whether an item file is in the scene now (true / "
                    "false, for an If)", "Is item in scene", group="Items", options={"file": self.item_files})

    def clicked(self, data: dict[str, Any]) -> None:
        """A click on the model, from VTS (ModelClickedEvent): the spot Record pin spot is waiting for."""
        if self._click is not None and not self._click.done():
            self._click.set_result(data)

    async def load_item(self, file: str, x: float = 0.0, y: float = 0.0, size: float = 0.3, rotation: float = 0.0,
                        order: int = 10, seconds: float = 0.5) -> str:
        answer = await self._request("ItemLoadRequest", {
            "fileName": file, "positionX": float(x), "positionY": float(y), "size": float(size),
            "rotation": float(rotation), "fadeTime": float(seconds), "order": int(order), "failIfOrderTaken": False,
            "smoothing": 0, "censored": False, "flipped": False, "locked": False,
            "unloadWhenPluginDisconnects": True})
        return answer["instanceID"]

    async def remove_items(self, instance: str = "") -> int:
        answer = await self._request("ItemUnloadRequest", {
            "unloadAllInScene": False, "unloadAllLoadedByThisPlugin": not instance,
            "allowUnloadingItemsLoadedByUserOrOtherPlugins": False,
            "instanceIDs": [instance] if instance else [], "fileNames": []})
        return len(answer.get("unloadedItems", []))

    async def move_item(self, instance: str, x: float, y: float, size: float = -1000, rotation: float = -1000,
                        seconds: float = 1.0) -> None:
        """size / rotation -1000 = keep as it is (VTS's rule)."""
        await self._request("ItemMoveRequest", {"itemsToMove": [{
            "itemInstanceID": instance, "timeInSeconds": float(seconds), "fadeMode": "easeBoth",
            "positionX": float(x), "positionY": float(y), "size": float(size), "rotation": float(rotation),
            "order": -1000, "setFlip": False, "flip": False, "userCanStop": True}]})

    async def pin_item(self, instance: str, pin_to: str = EXACT_SPOT, saved_spot: dict[str, Any] | None = None,
                       art_mesh: str = "", spot: str = "center", angle: Any = "", angle_from: str = "item",
                       size: Any = "") -> bool:
        """pin_to (PIN_TO) chooses the way: "exact spot" pins at saved_spot (from Record pin spot, kept in a
        variable), "model part" at art_mesh + spot; what the other way would use is ignored.
        VTS puts the item's middle on the spot. angle / size empty = the item keeps the ones it has; else the
        angle is counted from `angle_from` (ANGLE_FROM) and the size is the item's new size (0 to 1)."""
        pin_type, info = _pin_target(pin_to, saved_spot, art_mesh, spot)
        if angle_from not in ANGLE_FROM:
            raise ValueError(f"angle_from must be one of {', '.join(ANGLE_FROM)}, not {angle_from!r}")
        turn, resize = str(angle).strip() != "", str(size).strip() != ""
        info = {**info, "angle": float(angle) if turn else 0, "size": float(size) if resize else 0}
        answer = await self._request("ItemPinRequest", {
            "pin": True, "itemInstanceID": instance,
            "angleRelativeTo": ANGLE_FROM[angle_from if turn else "item"],
            "sizeRelativeTo": "RelativeToWorld" if resize else "RelativeToCurrentItemSize",
            "vertexPinType": pin_type, "pinInfo": info})
        return bool(answer.get("isPinned"))

    async def add_pinned_item(self, file: str, pin_to: str = EXACT_SPOT, saved_spot: dict[str, Any] | None = None,
                              art_mesh: str = "", spot: str = "center", size: float = 0.3, angle: float = 0.0,
                              angle_from: str = "model", order: int = 10, seconds: float = 0.5) -> dict[str, Any]:
        """Load item + Pin item in one: puts the item into the scene and pins its middle on the model. An
        item that can't be pinned (no such part, another model's spot) is taken out again."""
        _pin_target(pin_to, saved_spot, art_mesh, spot)  # a wrong setting fails before anything shows
        instance = await self.load_item(file, 0.0, 0.0, size, 0.0, order, seconds)
        try:
            pinned = await self.pin_item(instance, pin_to, saved_spot, art_mesh, spot, angle, angle_from)
        except Exception:
            await self.remove_items(instance)
            raise
        return {"instance": instance, "pinned": pinned}

    async def record_pin_spot(self, seconds: float = 20.0) -> dict[str, Any]:
        """Waits for the next click on the model in VTube Studio and gives back that exact spot (the topmost
        ArtMesh there, as VTS pins a dropped item): model, art_mesh, vertices and weights."""
        self._click = asyncio.get_running_loop().create_future()
        try:  # the client listens from the start (_listen), so a click right after subscribing isn't lost
            await self._request("EventSubscriptionRequest", {"eventName": CLICKED, "subscribe": True,
                                                             "config": {"onlyClicksOnModel": True}})  # connects
            data = await asyncio.wait_for(self._click, float(seconds))
        except asyncio.TimeoutError:
            raise TimeoutError(f"no click on the model within {seconds:g} seconds") from None
        finally:
            self._click = None
            await self._request("EventSubscriptionRequest", {"eventName": CLICKED, "subscribe": False})
        hits = sorted(data.get("artMeshHits", []), key=lambda h: h.get("artMeshOrder", 0))
        if not hits:
            raise ValueError("the click wasn't on the model")
        hit = hits[0]["hitInfo"]
        return {"model": data.get("loadedModelName", ""), "model_id": hit.get("modelID", ""),
                "art_mesh": hit.get("artMeshID", ""),
                "vertices": [hit.get(f"vertexID{i}") for i in (1, 2, 3)],
                "weights": [hit.get(f"vertexWeight{i}") for i in (1, 2, 3)]}

    async def unpin_item(self, instance: str) -> bool:
        return bool((await self._request("ItemPinRequest", {"pin": False, "itemInstanceID": instance}))
                    .get("isPinned"))

    async def art_mesh_names(self) -> list[str]:
        return sorted((await self._request("ArtMeshListRequest")).get("artMeshNames", []), key=str.casefold)

    async def item_in_scene(self, file: str) -> bool:
        """file = the item's file name, or its item scene name (what SAMMI's lizard timer checks)."""
        items = await self._request("ItemListRequest", {"includeItemInstancesInScene": True})
        wanted = file.casefold()
        return any(wanted in (i.get("fileName", "").casefold(), i.get("sceneName", "").casefold())
                   for i in items.get("itemInstancesInScene", []))

    async def item_files(self) -> list[str]:
        items = await self._request("ItemListRequest", {"includeAvailableItemFiles": True})
        return [i["fileName"] for i in items.get("availableItemFiles", [])]


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
