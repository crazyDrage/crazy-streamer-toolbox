import asyncio
import json
from typing import Any

import websockets


class FakeVtsServer:
    """A local websocket that answers like VTube Studio. `allow` decides the token popup; `requests` logs types."""

    def __init__(self, allow: bool = True, valid_tokens: tuple[str, ...] = ()) -> None:
        self.allow = allow
        self.valid_tokens = set(valid_tokens)
        self.requests: list[tuple[str, dict[str, Any]]] = []
        self.model = {"modelLoaded": True, "modelName": "Dragon", "modelID": "d1",
                      "modelPosition": {"positionX": 0.1, "positionY": -0.5, "rotation": 0.0, "size": -50.0}}
        self.subscribed: set[str] = set()
        self.load_seconds = 0.0  # how long a ModelLoadRequest takes (0 = at once)
        self._clients: list[Any] = []
        self._server: Any = None

    async def send_event(self, kind: str, data: dict[str, Any]) -> None:
        """An event like VTS sends by itself (with a requestID nobody asked for)."""
        for ws in list(self._clients):
            await ws.send(json.dumps({"requestID": "event", "messageType": kind, "data": data}))

    @property
    def url(self) -> str:
        port = self._server.sockets[0].getsockname()[1]
        return f"ws://127.0.0.1:{port}"

    async def __aenter__(self) -> "FakeVtsServer":
        self._server = await websockets.serve(self._handle, "127.0.0.1", 0)
        return self

    async def __aexit__(self, *exc: Any) -> None:
        self._server.close()
        await self._server.wait_closed()

    async def _handle(self, ws: Any) -> None:
        self._clients.append(ws)
        try:
            async for raw in ws:
                message = json.loads(raw)
                kind, data = message["messageType"], message.get("data", {})
                self.requests.append((kind, data))
                answer_type, answer = self._answer(kind, data)
                await ws.send(json.dumps({"requestID": message["requestID"], "messageType": answer_type,
                                          "data": answer}))
        finally:
            self._clients.remove(ws)

    def _answer(self, kind: str, data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        if kind == "AuthenticationTokenRequest":
            if not self.allow:
                return "APIError", {"errorID": 50, "message": "User has denied API access for your plugin."}
            self.valid_tokens.add("new-token")
            return "AuthenticationTokenResponse", {"authenticationToken": "new-token"}
        if kind == "AuthenticationRequest":
            ok = data.get("authenticationToken") in self.valid_tokens
            return "AuthenticationResponse", {"authenticated": ok, "reason": "" if ok else "Token invalid."}
        if kind == "APIStateRequest":
            return "APIStateResponse", {"active": True, "vTubeStudioVersion": "1.28.0"}
        if kind == "CurrentModelRequest":
            return "CurrentModelResponse", self.model
        if kind == "MoveModelRequest":
            self.model["modelPosition"] = {k: data[k] for k in ("positionX", "positionY", "rotation", "size")}
            return "MoveModelResponse", {}
        if kind == "HotkeysInCurrentModelRequest":
            return "HotkeysInCurrentModelResponse", {"availableHotkeys": [{"name": "tail on", "hotkeyID": "h1"}]}
        if kind == "HotkeyTriggerRequest":
            return "HotkeyTriggerResponse", {"hotkeyID": data["hotkeyID"]}
        if kind == "ItemListRequest":
            return "ItemListResponse", {
                "itemInstancesInScene": [{"fileName": "mini_lizard.png", "instanceID": "i1",
                                          "sceneName": "mini_lizard"}],
                "availableItemFiles": [{"fileName": "fan.png"}, {"fileName": "mini_lizard.png"}]}
        if kind == "ItemLoadRequest":
            return "ItemLoadResponse", {"instanceID": "i2", "fileName": data["fileName"]}
        if kind == "ItemUnloadRequest":
            return "ItemUnloadResponse", {"unloadedItems": [{"instanceID": "i2", "fileName": "fan.png"}]}
        if kind == "ExpressionStateRequest":
            files = [{"file": "fire_arm.exp3.json", "active": True}, {"file": "sad.exp3.json", "active": False}]
            wanted = data.get("expressionFile")
            return "ExpressionStateResponse", {"expressions": [e for e in files if not wanted or e["file"] == wanted]}
        if kind == "ExpressionActivationRequest":
            return "ExpressionActivationResponse", {}
        if kind == "ItemMoveRequest":
            return "ItemMoveResponse", {"movedItems": [{"itemInstanceID": i["itemInstanceID"], "success": True}
                                                       for i in data["itemsToMove"]]}
        if kind == "ItemPinRequest":
            return "ItemPinResponse", {"isPinned": data["pin"], "itemInstanceID": data["itemInstanceID"],
                                       "itemFileName": "hat.png"}
        if kind == "ArtMeshListRequest":
            return "ArtMeshListResponse", {"modelLoaded": True, "artMeshNames": ["head", "Hair_front", "arm_l"]}
        if kind == "AvailableModelsRequest":
            return "AvailableModelsResponse", {"availableModels": [{"modelName": "Dragon", "modelID": "d1"},
                                                                   {"modelName": "Human", "modelID": "h1"}]}
        if kind == "ModelLoadRequest":
            names = {"d1": "Dragon", "h1": "Human"}
            loaded = {**self.model, "modelLoaded": True, "modelName": names[data["modelID"]],
                      "modelID": data["modelID"]}
            if self.load_seconds:  # like VTS: no model for a moment, then the new one
                self.model = {**self.model, "modelLoaded": False}
                asyncio.get_running_loop().call_later(self.load_seconds, lambda: setattr(self, "model", loaded))
            else:
                self.model = loaded
            return "ModelLoadResponse", {"modelID": data["modelID"]}
        if kind == "EventSubscriptionRequest":
            self.subscribed.add(data["eventName"])
            return "EventSubscriptionResponse", {"subscribedEventCount": len(self.subscribed),
                                                 "subscribedEvents": sorted(self.subscribed)}
        return "APIError", {"errorID": 2, "message": f"unknown {kind}"}
