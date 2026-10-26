from typing import Any

from streamer_toolbox.connections.mixitup.boxes.mixitup_box import MixitupBox, _viewer_platforms


class GetViewer(MixitupBox):
    name = "get_user"
    label = "Get viewer"
    help = "A viewer as Mix It Up knows them: id, name, watch minutes, currencies and items by name"
    outputs = {"id": "text", "name": "text",
               "minutes": "number"}
    group = "Viewers"
    options = {"platform": _viewer_platforms}

    async def run(self, username: str, platform: str = "Twitch") -> dict[str, Any]:
        user = await self._user(username, platform)
        data = (user.get("PlatformData") or {}).get(platform or "Twitch") or {}
        currencies = {c["ID"]: c["Name"] for c in await self._send("GET", "currency") or []}
        return {"id": user["ID"], "name": data.get("DisplayName") or data.get("Username") or str(username),
                "minutes": user.get("OnlineViewingMinutes", 0),
                "currency": {currencies.get(k, k): v for k, v in (user.get("CurrencyAmounts") or {}).items()},
                "items": user.get("InventoryAmounts") or {}}
