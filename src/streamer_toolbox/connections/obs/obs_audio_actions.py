from typing import Any

from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.box_value import to_bool, to_list

MONITORING = {"off": "OBS_MONITORING_TYPE_NONE", "monitor only": "OBS_MONITORING_TYPE_MONITOR_ONLY",
              "monitor and output": "OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT"}
TRACKS = ("1", "2", "3", "4", "5", "6")


class ObsAudioActions:
    """OBS boxes for what the Audio Mixer's ⋮ → Advanced Audio Properties shows: monitoring (hear it yourself:
    off / monitor only / monitor and output), which of the 6 audio tracks a source goes to (recording / VOD
    tracks), and mute."""

    def __init__(self, requests: ObsRequests) -> None:
        self._requests = requests

    def add_to(self, actions: ActionRegistry) -> None:
        audio = {"group": "Audio"}
        actions.add("obs.set_audio_monitoring", self.set_monitoring, "Whether you hear a source yourself: off, "
                    "monitor only (you, not the stream) or monitor and output (both)", "Set audio monitoring",
                    options={"source": self._requests.input_names, "monitoring": _monitoring}, **audio)
        actions.add("obs.get_audio_monitoring", self.get_monitoring, "A source's monitoring: off, monitor only or "
                    "monitor and output", "Get audio monitoring", options={"source": self._requests.input_names},
                    **audio)
        actions.add("obs.set_audio_tracks", self.set_tracks, "Which audio tracks (1 to 6) a source goes to; the "
                    "others are switched off", "Set audio tracks", options={"source": self._requests.input_names},
                    hints={"tracks": "e.g. 1, 2 (or all, or none)"}, **audio)
        actions.add("obs.get_audio_tracks", self.get_tracks, "The audio tracks a source goes to, as a list like "
                    "[1, 2]", "Get audio tracks", options={"source": self._requests.input_names}, **audio)
        actions.add("obs.set_mute", self.set_mute, "Mutes or unmutes a source, or switches it the other way",
                    "Mute / unmute", options={"source": self._requests.input_names, "mute": _mute_choices},
                    **audio)
        actions.add("obs.get_mute", self.get_mute, "Whether a source is muted (true / false)", "Is muted",
                    options={"source": self._requests.input_names}, **audio)

    async def set_monitoring(self, source: str, monitoring: str = "monitor and output") -> None:
        await self._requests("SetInputAudioMonitorType", {"inputName": source,
                                                          "monitorType": monitor_type(monitoring)})

    async def get_monitoring(self, source: str) -> str:
        kind = (await self._requests("GetInputAudioMonitorType", {"inputName": source}))["monitorType"]
        return next((name for name, value in MONITORING.items() if value == kind), kind)

    async def set_tracks(self, source: str, tracks: Any = "1") -> list[int]:
        on = track_numbers(tracks)
        await self._requests("SetInputAudioTracks", {"inputName": source,
                                                     "inputAudioTracks": {t: t in on for t in TRACKS}})
        return [int(t) for t in on]

    async def get_tracks(self, source: str) -> list[int]:
        tracks = (await self._requests("GetInputAudioTracks", {"inputName": source}))["inputAudioTracks"]
        return [int(t) for t in TRACKS if tracks.get(t)]

    async def set_mute(self, source: str, mute: str = "mute") -> bool:
        if mute == "toggle":
            return (await self._requests("ToggleInputMute", {"inputName": source}))["inputMuted"]
        muted = mute != "unmute" and to_bool(mute)
        await self._requests("SetInputMute", {"inputName": source, "inputMuted": muted})
        return muted

    async def get_mute(self, source: str) -> bool:
        return (await self._requests("GetInputMute", {"inputName": source}))["inputMuted"]


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
