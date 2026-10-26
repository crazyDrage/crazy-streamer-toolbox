from typing import TYPE_CHECKING, Any

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.heartrate.heart_rate import HeartRate


class GetHeartRate(Box):
    name = "get"
    label = "Get heart rate"
    help = "The heart rate now, in beats per minute (0 before a service told one)"
    live = True
    outputs = {"bpm": "number", "source": "text"}

    def __init__(self, heart_rate: "HeartRate") -> None:
        self._heart_rate = heart_rate

    async def run(self) -> dict[str, Any]:
        return await self._heart_rate.get()
