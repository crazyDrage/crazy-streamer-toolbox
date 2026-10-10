from typing import Any

RATS, GEMS = "cur-rats", "cur-gems"


class FakeMixItUpCurrency:
    """Mix It Up's Developer API for currencies and viewers, in the shapes his real one answers with."""

    def __init__(self) -> None:
        self.amounts = {"u1": {RATS: 40, GEMS: 1}, "u2": {RATS: 7}, "u3": {}}
        self.names = {"u1": {"Twitch": "Kit"}, "u2": {"Twitch": "Vex", "YouTube": "VexTube"}, "u3": {"Twitch": "New"}}
        self.calls: list[tuple[str, str]] = []

    async def send(self, method: str, path: str, **kwargs: Any) -> Any:
        self.calls.append((method, path))
        if path == "currency":
            return [{"ID": RATS, "Name": "rats"}, {"ID": GEMS, "Name": "Gems"}]
        if path == "users":
            skip, size = kwargs["params"]["skip"], kwargs["params"]["pageSize"]
            ids = sorted(self.names)[skip:skip + size]
            return {"TotalCount": len(self.names), "Users": [{
                "ID": uid, "CurrencyAmounts": self.amounts[uid],
                "PlatformData": {p: {"Username": n.casefold(), "DisplayName": n} for p, n in self.names[uid].items()}}
                for uid in ids]}
        if path.startswith("users/"):
            _, platform, name = path.split("/")
            found = next((uid for uid, names in self.names.items()
                          if names.get(platform, "").casefold() == name.casefold()), None)
            if found is None:
                raise RuntimeError("Mix It Up: User not found")
            return {"User": {"ID": found}}
        _, currency, uid = path.split("/")
        if method == "GET":
            return {"Amount": self.amounts[uid].get(currency, 0)}
        amount = kwargs["json"]["Amount"]
        self.amounts[uid][currency] = amount if method == "PUT" else self.amounts[uid].get(currency, 0) + amount
        return None
