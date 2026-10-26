from streamer_toolbox.connections.lumia.boxes.lumia_box import LumiaBox


class SetLumiaLights(LumiaBox):
    name = "color"
    label = "Set Lumia lights"
    help = "Sets the lights to a colour for some seconds"
    hints = {
"color": "Like #FF4076", "brightness": "0 to 100", "seconds": "How long it stays",
"fade": "Seconds the change takes", "hold": "Yes: the lights stay like this"}

    async def run(self, color: str = "#FF4076", brightness: float = 100, seconds: float = 4,
                  fade: float = 0, hold: bool = False) -> None:
        color = str(color).strip()
        if not (color.startswith("#") and len(color) == 7):
            raise ValueError("The colour must look like #FF4076")
        await self._send({"type": "hex-color", "params": {
            "value": color, "brightness": min(max(float(brightness), 0), 100),
            "transition": int(max(float(fade), 0) * 1000), "duration": int(max(float(seconds), 0) * 1000),
            **({"hold": True} if hold else {})}})
