from streamer_toolbox.connections.obs.boxes.obs_output_box import ObsOutputBox, RECORD, _choices, _request


class Recording(ObsOutputBox):
    name = "record"
    label = "Recording"
    help = "Starts, stops, pauses or resumes recording; stop gives the file"
    options = {"action": _choices(RECORD)}
    group = "Recording / streaming"

    async def run(self, action: str = "toggle") -> str:
        answer = await self._requests(_request(RECORD, action))
        return answer.get("outputPath", "")
