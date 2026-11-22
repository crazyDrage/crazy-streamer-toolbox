import json
import uuid
from typing import Any

# Warudo's own type ids, from his export (11-21: temp/feedback/warudo/)
ASSET_TYPE = "com.veasu.templatedwebsocketasset"  # the plugin's "Send Websocket Asset"
ON_ACTION = "61445859-8471-4baa-88d6-b186773bd40d"  # On WebSocket Action
SET_PROPERTY = "38f1c043-559d-478b-a465-feba333e6c90"  # Set Asset Property
STRING_DATA = '{"label":"String","value":4,"description":null,"icon":null}'
EASING = '{"label":"OutCubic","value":9,"description":null,"icon":null}'
# the first Set Asset Property sets this, so the real address after it is a change and the asset connects again
PLACEHOLDER = "ws://localhost:1/reconnect"
IDS = uuid.UUID("6f0c2a1e-3d4b-4c5a-9e8f-7a6b5c4d3e2f")  # the ids below are made from this and the type


def connect_action(kind: str) -> str:
    """The On WebSocket Action's name that makes the asset of this type connect again."""
    return f"connect_input_{kind}"


class WarudoCopyTexts:
    """What the Warudo tab's Copy asset / Copy blueprint buttons give (his 11-21), made from his own export:
    an asset "Send Websocket Asset" with the address, and his blueprint "toolbox_connect_input_<type>": On
    WebSocket Action connect_input_<type> (data: text) → Set Asset Property WSAddr to a placeholder → Set Asset
    Property WSAddr to the text that came. The toolbox sends that action with the address (the default flow
    "Warudo - default - connect input"), so the asset connects again after the toolbox was closed.

    The ids come from the type, so the blueprint copied for a type finds the asset copied for it."""

    def asset(self, kind: str, address: str) -> str:
        return json.dumps({"id": self._id("asset", kind),
                           "dataInputs": {"WSAddr": {"type": "string", "value": json.dumps(address)}},
                           "typeId": ASSET_TYPE, "name": self._asset_name(kind), "active": True, "order": 0,
                           "group": None})

    def blueprint(self, kind: str) -> str:
        on_action, first, second = (self._id(part, kind) for part in ("on_action", "set_placeholder", "set_address"))
        nodes: dict[str, Any] = {
            on_action: {"id": on_action, "typeId": ON_ACTION, "name": "ON_WEBSOCKET_ACTION", "x": -514.5, "y": -254.0,
                        "dataInputs": {"Action": {"type": "string", "value": json.dumps(connect_action(kind))},
                                       "DataType": {"type": "Warudo.Plugins.Core.Nodes.External.WebSocketActionDataType",
                                                    "value": STRING_DATA}}},
            first: self._set_node(first, kind, PLACEHOLDER, -231.1, -343.7),
            second: self._set_node(second, kind, "", 59.0, -431.0),
        }
        return json.dumps({
            "id": self._id("blueprint", kind), "enabled": True, "name": f"toolbox_connect_input_{kind}", "order": 0,
            "group": None, "panningX": 653.5, "panningY": 442.0, "scaling": 1.0, "nodes": nodes,
            "dataConnections": [{"outputNode": on_action, "inputNode": second, "outputPort": "StringData",
                                 "inputPort": "TargetValue"}],
            "flowConnections": [{"outputNode": on_action, "inputNode": first, "outputPort": "Exit", "inputPort": "Enter"},
                                {"outputNode": first, "inputNode": second, "outputPort": "Exit", "inputPort": "Enter"}],
            "properties": {"id": self._id("properties", kind),
                           "dataInputs": {"Variables": {"type": "Warudo.Core.Graphs.GraphVariable[]", "value": "[]"}}}})

    def _set_node(self, node_id: str, kind: str, value: str, x: float, y: float) -> dict[str, Any]:
        asset = json.dumps({"id": self._id("asset", kind), "name": self._asset_name(kind)})
        return {"id": node_id, "typeId": SET_PROPERTY, "name": "SET_ASSET_PROPERTY", "x": x, "y": y,
                "dataInputs": {"Asset": {"type": "Warudo.Core.Scenes.Asset", "value": asset},
                               "DataPath": {"type": "string", "value": json.dumps("WSAddr")},
                               "DisableClientUpdates": {"type": "bool", "value": "false"},
                               "TransitionTime": {"type": "float", "value": "0.0"},
                               "TransitionEasing": {"type": "DG.Tweening.Ease", "value": EASING},
                               "Toggle": {"type": "bool", "value": "false"},
                               "SerializedTargetValue": {"type": "string", "value": json.dumps(json.dumps(value))},
                               "TargetValue": {"type": "string", "value": json.dumps(value)}}}

    @staticmethod
    def _asset_name(kind: str) -> str:
        return f"toolbox_input_{kind}"

    @staticmethod
    def _id(part: str, kind: str) -> str:
        return str(uuid.uuid5(IDS, f"{part}:{kind}"))
