import json
from urllib.parse import unquote

import httpx

CURRENCY_ID = "id-rats"
USER_ID = "id-viewer"


class FakeMixItUp:
    """Mix It Up's Developer API v2 in memory, answering like the real one (checked on his 1.8 with GETs):
    commands with a Type, one currency (rats), one inventory, counters by name, viewers wrapped in "User", a 404
    with {"title", "detail"} for an unknown viewer or counter."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.commands = [{"ID": "id-hammer", "Name": "hammer_bong", "Type": "Chat"},
                         {"ID": "id-desktop", "Name": "desktop_scene_dragon", "Type": "Action Group"},
                         {"ID": "id-magic", "Name": "Magic 8 Ball", "Type": "Pre-Made"}]
        self.rats = 42
        self.items = {"id-sword": 1}
        self.counters: dict[str, float] = {"deaths": 3}

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._answer)

    def sent(self, method: str) -> list[tuple[str, dict]]:
        """(path after /api/v2/, json body) of every request with that method."""
        return [(unquote(r.url.raw_path.decode()).split("/api/v2/", 1)[1], json.loads(r.content or b"{}"))
                for r in self.requests if r.method == method]

    def _answer(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        parts = [unquote(p) for p in request.url.raw_path.decode().split("?")[0].split("/api/v2/", 1)[1].split("/")]
        body = json.loads(request.content or b"{}")
        if parts == ["status", "version"]:
            return httpx.Response(200, text="1.8.201.0")
        if parts == ["commands"]:
            return httpx.Response(200, json={"TotalCount": len(self.commands), "Commands": self.commands})
        if parts == ["currency"]:
            return httpx.Response(200, json=[{"ID": CURRENCY_ID, "Name": "rats"}])
        if parts == ["inventory"]:
            return httpx.Response(200, json=[{"ID": "id-bag", "Name": "Bag",
                                              "Items": [{"ID": "id-sword", "Name": "Sword"}]}])
        if parts[0] == "users":
            if parts[2].casefold() != "viewer":
                return _not_found(f"User '{parts[2]}' not found on platform '{parts[1]}'")
            return httpx.Response(200, json={"User": {
                "ID": USER_ID, "OnlineViewingMinutes": 90, "CurrencyAmounts": {CURRENCY_ID: self.rats},
                "InventoryAmounts": {}, "PlatformData": {"Twitch": {"Username": "viewer", "DisplayName": "Viewer"}}}})
        if parts[0] == "currency":
            if request.method == "PATCH":
                self.rats += body["Amount"]
            elif request.method == "PUT":
                self.rats = body["Amount"]
            return httpx.Response(200, json={"CurrencyName": "rats", "UserID": USER_ID, "Amount": self.rats})
        if parts[0] == "inventory":
            item = parts[2]
            if request.method == "PATCH":
                self.items[item] = self.items.get(item, 0) + body["Amount"]
            elif request.method == "PUT":
                self.items[item] = body["Amount"]
            return httpx.Response(200, json={"Amount": self.items.get(item, 0)})
        if parts == ["counters"]:
            if request.method == "POST":
                self.counters[body["Name"]] = 0
                return httpx.Response(200)
            return httpx.Response(200, json={"TotalCount": len(self.counters),
                                             "Counters": [{"Name": n} for n in self.counters]})
        if parts[0] == "counters":
            name = parts[1]
            if name not in self.counters:
                return _not_found(f"Counter '{name}' not found")
            if parts[2:] == ["update"]:
                self.counters[name] += body["Amount"]
            elif parts[2:] == ["set"]:
                self.counters[name] = body["Amount"]
            elif parts[2:] == ["reset"]:
                self.counters[name] = 0
            return httpx.Response(200, json={"Name": name, "Amount": self.counters[name]})
        return httpx.Response(200)


def _not_found(detail: str) -> httpx.Response:
    return httpx.Response(404, json={"title": "Not Found", "status": 404, "detail": detail})
