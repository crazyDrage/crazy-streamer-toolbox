from streamer_toolbox.connections.obs.boxes.obs_new_source_box import ObsNewSourceBox
from streamer_toolbox.connections.obs.obs_requests import ObsRequests


class RemoveSource(ObsNewSourceBox):
    name = "remove_source"
    label = "Remove source"
    help = "Removes a source from OBS: from every scene, with its settings and filters (like Remove in OBS; it " \
           "can't be undone)"
    group = "Sources"

    def __init__(self, requests: ObsRequests) -> None:
        super().__init__(requests)
        self.options = {"source": self._requests.input_names}

    async def run(self, source: str) -> None:
        await self._requests("RemoveInput", {"inputName": source})
