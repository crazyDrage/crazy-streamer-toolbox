from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.interfaces.point_bank import PointBank

Send = Callable[..., Awaitable[Any]]
PLATFORMS = {"twitch": "Twitch", "youtube": "YouTube", "trovo": "Trovo"}
PAGE = 100


class MixItUpPointBank(PointBank):
    """The points in Mix It Up: one of its currencies (his: "rats"), through its Developer API. Mix It Up keeps
    giving them out by its own rules; the toolbox's Points boxes and the points command read and change the
    same numbers. `currency` gives the currency's name as set on the Points page ("" = Mix It Up's first one).

    viewers() lists everyone with an amount, for moving the amounts over into the toolbox's own store. The
    list's shape is from his real Mix It Up (2026-10-05): {"TotalCount", "Users": [{"ID", "CurrencyAmounts":
    {currency id: amount}, "PlatformData": {"Twitch": {"Username", "DisplayName"}}}]}, paged by skip /
    pageSize."""

    def __init__(self, send: Send, currency: Callable[[], str] = lambda: "") -> None:
        self._send = send
        self._currency = currency

    async def currencies(self) -> list[str]:
        return [str(one["Name"]) for one in await self._send("GET", "currency") or []]

    async def get(self, viewer: str, platform: str = "twitch") -> int:
        answer = await self._send("GET", f"currency/{await self._id()}/{await self._user(viewer, platform)}")
        return _amount(answer)

    async def add(self, viewer: str, amount: int, platform: str = "twitch") -> int:
        path = f"currency/{await self._id()}/{await self._user(viewer, platform)}"
        have = _amount(await self._send("GET", path))
        await self._send("PATCH", path, json={"Amount": max(int(amount), -have)})  # never below 0
        return _amount(await self._send("GET", path))

    async def set(self, viewer: str, points: int, platform: str = "twitch") -> int:
        path = f"currency/{await self._id()}/{await self._user(viewer, platform)}"
        await self._send("PUT", path, json={"Amount": max(0, int(points))})
        return max(0, int(points))

    async def spend(self, viewer: str, amount: int, platform: str = "twitch") -> bool:
        path = f"currency/{await self._id()}/{await self._user(viewer, platform)}"
        if int(amount) < 0 or _amount(await self._send("GET", path)) < int(amount):
            return False
        await self._send("PATCH", path, json={"Amount": -int(amount)})
        return True

    async def top(self, count: int = 10) -> list[dict[str, Any]]:
        ranked = sorted(await self.viewers(), key=lambda one: (-one["points"], one["user"].casefold()))
        return ranked[:max(0, int(count))]

    async def viewers(self) -> list[dict[str, Any]]:
        """Everyone with some of the currency: [{"user", "platform", "points"}] (a viewer known on two
        platforms is listed for each)."""
        currency = await self._id()
        found: list[dict[str, Any]] = []
        skip = 0
        while True:
            answer = await self._send("GET", "users", params={"skip": skip, "pageSize": PAGE})
            users = answer.get("Users") if isinstance(answer, dict) else answer
            users = users if isinstance(users, list) else []
            for user in users:
                points = _amount((user.get("CurrencyAmounts") or {}).get(currency))
                for platform, data in (user.get("PlatformData") or {}).items():
                    name = str((data or {}).get("DisplayName") or (data or {}).get("Username") or "")
                    if points > 0 and name:
                        found.append({"user": name, "platform": str(platform).casefold(), "points": points})
            skip += PAGE
            total = answer.get("TotalCount") if isinstance(answer, dict) else None
            if len(users) < PAGE or (isinstance(total, int) and skip >= total):
                return found

    async def _id(self) -> str:
        currencies = await self._send("GET", "currency") or []
        wanted = self._currency().strip().casefold()
        found = next((one["ID"] for one in currencies if not wanted or str(one["Name"]).casefold() == wanted), None)
        if found is None:
            raise LookupError(f"Mix It Up has no currency named {self._currency()!r}" if wanted
                           else "Mix It Up has no currency yet")
        return found

    async def _user(self, viewer: str, platform: str) -> str:
        name = str(viewer).strip().lstrip("@")
        if not name:
            raise ValueError("a viewer's name is needed")
        where = PLATFORMS.get(str(platform or "twitch").casefold(), "Twitch")
        answer = await self._send("GET", f"users/{where}/{name}")
        user = answer.get("User", answer) if isinstance(answer, dict) else None
        if not isinstance(user, dict) or "ID" not in user:
            raise LookupError(f"Mix It Up doesn't know the viewer {name!r} on {where}")
        return user["ID"]


def _amount(value: Any) -> int:
    if isinstance(value, dict):
        value = value.get("Amount", value.get("Value", 0))
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
