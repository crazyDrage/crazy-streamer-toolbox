import asyncio
from typing import Any

from streamer_toolbox.connections.vtube_studio.boxes.add_item_pinned_to_model import AddItemPinnedToModel
from streamer_toolbox.connections.vtube_studio.boxes.is_item_in_scene import IsItemInScene
from streamer_toolbox.connections.vtube_studio.boxes.load_item import LoadItem
from streamer_toolbox.connections.vtube_studio.boxes.move_item import MoveItem
from streamer_toolbox.connections.vtube_studio.boxes.pin_item_to_model import PinItemToModel
from streamer_toolbox.connections.vtube_studio.boxes.record_pin_spot import RecordPinSpot
from streamer_toolbox.connections.vtube_studio.boxes.remove_items import RemoveItems
from streamer_toolbox.connections.vtube_studio.boxes.unpin_item import UnpinItem
from streamer_toolbox.connections.vtube_studio.boxes.vts_item_shared import (ANGLE_FROM, CLICKED, EXACT_SPOT, Request,
                                                                             _pin_target)
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class VtsItemActions:
    """VTube Studio boxes for items (pictures from VTS's Items folder): put one into the scene, move it, take it
    out, pin it onto the model (on an exact spot recorded by a click on the model, or on a model part), and
    whether one is in the scene. The connection hands it the clicks VTS reports (clicked)."""

    def __init__(self, request: Request) -> None:
        self._request = request
        self._click: asyncio.Future | None = None  # Record pin spot waits on it

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (LoadItem(self), RemoveItems(self), MoveItem(self), AddItemPinnedToModel(self),
                    PinItemToModel(self), RecordPinSpot(self), UnpinItem(self), IsItemInScene(self)):
            actions.add_box(box, "vts")

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


