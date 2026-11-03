from typing import Any

from streamer_toolbox.connections.obs.boxes.obs_audio_box import MONITORING

STARTED = ("OBS_MEDIA_STATE_PLAYING", "OBS_MEDIA_STATE_PAUSED", "OBS_MEDIA_STATE_BUFFERING")
FINISHED = ("OBS_MEDIA_STATE_ENDED", "OBS_MEDIA_STATE_ERROR")
ADDRESS_STARTS = ("http://", "https://")  # a "file" that starts like this is played from the internet
# what a placed copy takes over from the source it is placed like (the rest are OBS's read-only facts)
PLACE = ("positionX", "positionY", "rotation", "alignment", "boundsAlignment", "cropLeft", "cropRight", "cropTop",
         "cropBottom")


def _seconds(milliseconds: Any) -> float:
    """OBS gives media times in ms, or nothing / -1 when it doesn't know (yet)."""
    if not isinstance(milliseconds, (int, float)) or milliseconds < 0:
        return 0.0
    return round(milliseconds / 1000, 3)


async def _monitoring() -> list[str]:
    return list(MONITORING)
