from typing import Any

from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.data.box_value import to_list
from streamer_toolbox.core.interfaces.box import Box


MONITORING = {"off": "OBS_MONITORING_TYPE_NONE", "monitor only": "OBS_MONITORING_TYPE_MONITOR_ONLY",
              "monitor and output": "OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT"}
TRACKS = ("1", "2", "3", "4", "5", "6")


class ObsAudioBox(Box):
    """What the obs audio boxes share (not a box itself: it has no run).

    OBS boxes for what the Audio Mixer's ⋮ → Advanced Audio Properties shows: monitoring (hear it yourself:
    off / monitor only / monitor and output), which of the 6 audio tracks a source goes to (recording / VOD
    tracks), and mute."""

    def __init__(self, requests: ObsRequests) -> None:
        self._requests = requests


def monitor_type(monitoring: str) -> str:
    """off / monitor only / monitor and output (or OBS's own OBS_MONITORING_TYPE_... name) → OBS's name."""
    if monitoring in MONITORING.values():
        return monitoring
    key = str(monitoring).strip().casefold()
    if key not in MONITORING:
        raise ValueError(f"monitoring is one of {', '.join(MONITORING)}, not {monitoring!r}")
    return MONITORING[key]


def track_numbers(tracks: Any) -> list[str]:
    """"1, 2" / "1 2" / [1, 2] / "[1, 2]" / 3 / "all" / "none" → ["1", "2"]."""
    text = str(tracks).strip()
    if text.casefold() == "all":
        return list(TRACKS)
    if text.casefold() in ("none", ""):
        return []
    if isinstance(tracks, (list, int, float)):
        items = tracks if isinstance(tracks, list) else [tracks]
    else:
        items = to_list(text) if text.startswith("[") else text.replace(",", " ").split()
    try:
        numbers = [str(int(float(t))) for t in items]
    except (TypeError, ValueError):
        raise ValueError(f"tracks are numbers 1 to 6 like 1, 2; not {tracks!r}") from None
    wrong = [t for t in numbers if t not in TRACKS]
    if wrong:
        raise ValueError(f"OBS has audio tracks 1 to 6, not {', '.join(wrong)}")
    return [t for t in TRACKS if t in numbers]


async def _monitoring() -> list[str]:
    return list(MONITORING)


async def _mute_choices() -> list[str]:
    return ["mute", "unmute", "toggle"]
