from streamer_toolbox.connections.tits.boxes.tits_box import TitsBox, Ask, _find


class ThrowItem(TitsBox):
    name = "throw"
    label = "Throw item"
    help = "Throws items at the model: one kind, or several kinds mixed (T.I.T.S. picks among the ticked ones " \
           "for each throw)"
    outputs = {"thrown": "number"}
    hints = {"item": "One item, or several (the list button): then each throw is one of them",
             "amount": "How many throws in all", "delay": "Seconds between two throws, e.g. 0.05"}

    def __init__(self, ask: Ask) -> None:
        super().__init__(ask)
        self.many = {"item": self.item_names}

    async def run(self, item: str, amount: int = 1, delay: float = 0.05) -> dict[str, int]:
        known = await self._items()
        names = [name for name in str(item if item is not None else "").split(",") if name.strip()] or [""]
        answer = await self._ask("TITSThrowItemsRequest", {
            "items": [_find(known, name, "item") for name in names], "delayTime": max(float(delay), 0),
            "amountOfThrows": max(int(amount), 1), "errorOnMissingID": True})
        return {"thrown": int(answer.get("numberOfThrownItems") or 0)}
