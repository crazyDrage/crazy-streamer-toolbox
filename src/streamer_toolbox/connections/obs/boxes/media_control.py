from streamer_toolbox.connections.obs.boxes.obs_source_box import ObsSourceBox, Call, MEDIA_ACTIONS


class MediaControl(ObsSourceBox):
    name = "media_control"
    label = "Media control"
    help = "Restarts, plays, pauses or stops a Media Source"
    group = "Media"

    def __init__(self, call: Call) -> None:
        super().__init__(call)
        self.options = {"source": self.media_names, "action": self.media_action_names}

    async def run(self, source: str, action: str = "restart") -> None:
        if action not in MEDIA_ACTIONS:
            raise ValueError(f"unknown media action {action!r}; use one of {', '.join(MEDIA_ACTIONS)}")
        await self._request("TriggerMediaInputAction", {"inputName": source, "mediaAction": MEDIA_ACTIONS[action]})
