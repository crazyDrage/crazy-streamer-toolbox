from streamer_toolbox.connections.obs.boxes.obs_output_box import ObsOutputBox


class ObsStats(ObsOutputBox):
    name = "get_stats"
    label = "OBS stats"
    help = "OBS's numbers: CPU %, memory MB, FPS, dropped frames"
    group = "Advanced"
    live = True
    outputs = {"cpu": "number", "memory_mb": "number", "fps": "number",
               "render_skipped": "number", "output_skipped": "number"}

    async def run(self) -> dict[str, float]:
        s = await self._requests("GetStats")
        return {"cpu": round(s.get("cpuUsage", 0), 1), "memory_mb": round(s.get("memoryUsage", 0)),
                "fps": round(s.get("activeFps", 0), 1), "render_skipped": s.get("renderSkippedFrames", 0),
                "output_skipped": s.get("outputSkippedFrames", 0)}
