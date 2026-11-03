from typing import Any

from streamer_toolbox.connections.obs.boxes.obs_output_box import ObsOutputBox


class LiveRecording(ObsOutputBox):
    name = "get_output_status"
    label = "Live / recording?"
    help = "Whether you're live, recording, and for how long"
    outputs = {"streaming": "yes/no", "recording": "yes/no",
               "stream_seconds": "number", "record_seconds": "number"}
    live = True
    group = "Recording / streaming"

    async def run(self) -> dict[str, Any]:
        stream = await self._requests("GetStreamStatus")
        record = await self._requests("GetRecordStatus")
        return {"streaming": bool(stream.get("outputActive")), "recording": bool(record.get("outputActive")),
                "stream_seconds": round(stream.get("outputDuration", 0) / 1000),
                "record_seconds": round(record.get("outputDuration", 0) / 1000)}
