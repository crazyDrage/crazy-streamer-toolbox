import json
from functools import cache
from pathlib import Path
from typing import Any

PROTOCOL_FOLDER = Path(__file__).with_name("protocol")
# one file per category ("scene_items.json": {"category": "scene items", "requests": {name: {description,
# fields}}}), made from obs-websocket's docs/generated/protocol.json (github.com/obsproject/obs-websocket,
# master, 2026-10-02): deprecated requests left out; per request its first description line and request fields
TYPES = {"String": "text", "Number": "number", "Boolean": "yes/no", "Object": "object", "Array": "list",
         "Any": "any"}
EXAMPLES = {"String": "", "Number": 0, "Boolean": True, "Object": {}, "Array": [], "Any": ""}


class ObsProtocol:
    """What each obs-websocket request needs, for the Raw request box: the requests by category (the picker), a
    data template with the fields to fill in, and a hint naming them all."""

    def __init__(self, requests: dict[str, dict[str, Any]] | None = None) -> None:
        self._requests = requests if requests is not None else _load()

    def by_category(self, available: list[str] | None = None) -> dict[str, dict[str, str]]:
        """Category ("Scene items") → {request: request}; requests OBS has that the file doesn't know go under
        Other, requests it doesn't have (an older OBS) are left out."""
        groups: dict[str, dict[str, str]] = {}
        for name, request in self._requests.items():
            if available is None or name in available:
                groups.setdefault(request["category"].capitalize(), {})[name] = name
        for name in sorted(set(available or []) - set(self._requests), key=str.casefold):
            groups.setdefault("Other", {})[name] = name
        return dict(sorted(groups.items()))

    def template(self, request: Any) -> dict[str, Any]:
        """{"data": JSON text with the fields to fill in}: the ones it needs, and for a thing named either by name
        or by UUID (sceneName / sceneUuid) the name one. Nothing for a request without fields or one it doesn't
        know."""
        fields = self._fields(request)
        names = {f["name"] for f in fields}
        wanted = {f["name"]: EXAMPLES.get(f["type"], "") for f in fields
                  if not f["optional"] or (f["name"].endswith("Name") and f["name"][:-4] + "Uuid" in names)}
        return {"data": json.dumps(wanted, ensure_ascii=False)} if wanted else {}

    def hint(self, params: dict[str, Any]) -> str:
        """For the data field: what the picked request does, the fields it needs and the ones it may have."""
        request = params.get("request", "")
        if request not in self._requests:
            return "pick a request: its fields are filled in here" if not request else \
                "data as JSON text like {\"sceneName\": \"desktop\"}"
        fields = self._fields(request)
        text = self._requests[request]["description"]
        needed = [_field(f) for f in fields if not f["optional"]]
        maybe = [_field(f) for f in fields if f["optional"] and f["name"] != "canvasUuid"]
        if needed:
            text += f" Needs: {', '.join(needed)}."
        if maybe:
            text += f" May have: {', '.join(maybe)}."
        return text if fields else text + " No data needed."

    def _fields(self, request: Any) -> list[dict[str, Any]]:
        return self._requests.get(str(request), {}).get("fields", [])


def _field(field: dict[str, Any]) -> str:
    return f"{field['name']} ({TYPES.get(field['type'], field['type'].lower())})"


@cache
def _load() -> dict[str, dict[str, Any]]:
    requests: dict[str, dict[str, Any]] = {}
    for file in sorted(PROTOCOL_FOLDER.glob("*.json")):
        part = json.loads(file.read_text(encoding="utf-8"))
        for name, request in part["requests"].items():
            requests[name] = {"category": part["category"], **request}
    return requests
