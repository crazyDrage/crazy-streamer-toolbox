from streamer_toolbox.connections.tits.boxes.tits_box import TitsBox, Ask, PICTURE, _find


class GetTITSItem(TitsBox):
    name = "get_item"
    label = "Get T.I.T.S. item"
    help = "One item of T.I.T.S. with its picture, e.g. to show what was thrown in a widget (picture = an " \
           "address a web page can show as it is)"
    outputs = {"name": "text", "item_id": "text", "picture": "text"}
    hints = {"item": "Its name; wire the hit trigger's item into it"}

    def __init__(self, ask: Ask) -> None:
        super().__init__(ask)
        self.options = {"item": self.item_names}

    async def run(self, item: str) -> dict[str, str]:
        item_id = _find(await self._items(), item, "item")
        answer = await self._ask("TITSItemInfoRequest", {"itemID": item_id, "sendImage": True})
        picture = str(answer.get("encodedImage") or "")
        return {"name": str(answer.get("name") or item).strip(), "item_id": item_id,
                "picture": PICTURE + picture if picture else ""}
