from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.interfaces.box import Box

Ask = Callable[..., Awaitable[dict[str, Any]]]
NO_EFFECT = "No effect"
RANDOM = ["AllVoices", "FreeVoices", "FavoriteVoices", "CustomVoices"]
TOGGLES = {"Voice changer": "toggleVoiceChanger", "Hear myself": "toggleHearMyVoice",
           "Mute microphone": "toggleMuteMic", "Background effects": "toggleBackground"}


class VoicemodBox(Box):
    """What the voicemod boxes share (not a box itself: it has no run).

    Voicemod's boxes, over its Control API (control-api.voicemod.net): switch the voice, play a
    soundboard sound, flip one of its switches. Voices and sounds are picked by name (the pickers list them
    from the running program); the id is looked up."""

    def __init__(self, ask: Ask) -> None:
        self._ask = ask

    async def voice_names(self) -> list[str]:
        try:
            return [NO_EFFECT, *sorted(await self._voices())]
        except ConnectionError:
            return []

    async def sound_names(self) -> list[str]:
        try:
            return sorted(await self._sounds())
        except ConnectionError:
            return []

    @staticmethod
    async def random_kinds() -> list[str]:
        return list(RANDOM)

    @staticmethod
    async def switches() -> list[str]:
        return list(TOGGLES)

    async def _voices(self) -> dict[str, str]:
        """name → id, only the voices this Voicemod can use"""
        voices = (await self._ask("getVoices", {})).get("voices")
        return {str(v.get("friendlyName") or v.get("id")): str(v.get("id") or "")
                for v in voices or [] if isinstance(v, dict) and v.get("enabled", True)}

    async def _sounds(self) -> dict[str, str]:
        """name → file name"""
        sounds = (await self._ask("getMemes", {})).get("listOfMemes")
        return {str(s.get("Name") or s.get("FileName")): str(s.get("FileName") or s.get("Filename") or "")
                for s in sounds or [] if isinstance(s, dict)}


def _find(known: dict[str, str], name: str, what: str) -> str:
    wanted = str(name).strip()
    found = known.get(wanted) or next((i for n, i in known.items() if n.casefold() == wanted.casefold()), None)
    if found is None:
        raise KeyError(f"Voicemod has no {what} named {wanted!r}")
    return found
