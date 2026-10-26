from streamer_toolbox.connections.tits.boxes.tits_box import TitsBox, Ask, _find


class ActivateTrigger(TitsBox):
    name = "activate_trigger"
    label = "Activate trigger"
    help = "Activates a trigger made in T.I.T.S."

    def __init__(self, ask: Ask) -> None:
        super().__init__(ask)
        self.options = {"trigger": self.trigger_names}

    async def run(self, trigger: str) -> None:
        triggers = await self._triggers()
        trigger_id = _find(triggers, trigger, "trigger")
        name = next(n for n, i in triggers.items() if i == trigger_id)
        await self._ask("TITSTriggerActivateRequest", {"triggerID": trigger_id, "triggerName": name})
