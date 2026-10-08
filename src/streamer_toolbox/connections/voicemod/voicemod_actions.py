from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry

Ask = Callable[..., Awaitable[dict[str, Any]]]  # ask(action, payload, answered=True) → what Voicemod said
NO_EFFECT = "No effect"  # Voicemod's own voice id for "clean": nofx
RANDOM = ["AllVoices", "FreeVoices", "FavoriteVoices", "CustomVoices"]
TOGGLES = {"Voice changer": "toggleVoiceChanger", "Hear myself": "toggleHearMyVoice",
           "Mute microphone": "toggleMuteMic", "Background effects": "toggleBackground"}


class VoicemodActions:
    """Voicemod's boxes, over its Control API (control-api.voicemod.net): switch the voice, play a
    soundboard sound, flip one of its switches. Voices and sounds are picked by name (the pickers list them
    from the running program); the id is looked up."""

    def __init__(self, ask: Ask) -> None:
        self._ask = ask

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("voicemod.voice", self.voice, "Switches Voicemod to a voice", "Set Voicemod voice",
                    options={"voice": self.voice_names})
        actions.add("voicemod.random_voice", self.random_voice, "Switches Voicemod to a random voice",
                    "Random Voicemod voice", options={"among": self.random_kinds})
        actions.add("voicemod.play_sound", self.play_sound, "Plays a sound of Voicemod's soundboard",
                    "Play Voicemod sound", group="Soundboard", options={"sound": self.sound_names})
        actions.add("voicemod.stop_sounds", self.stop_sounds, "Stops every soundboard sound",
                    "Stop Voicemod sounds", group="Soundboard")
        actions.add("voicemod.toggle", self.toggle, "Flips one of Voicemod's switches; tells how it is now",
                    "Flip Voicemod switch", options={"switch": self.switches}, outputs={"on": "yes/no"})

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

    async def voice(self, voice: str) -> None:
        wanted = str(voice).strip()
        voice_id = "nofx" if wanted.casefold() in (NO_EFFECT.casefold(), "nofx") \
            else _find(await self._voices(), wanted, "voice")
        await self._ask("loadVoice", {"voiceID": voice_id}, answered=False)

    async def random_voice(self, among: str = "AllVoices") -> None:
        if among not in RANDOM:
            raise ValueError(f"Among which voices? One of {', '.join(RANDOM)}")
        await self._ask("selectRandomVoice", {"mode": among}, answered=False)

    async def play_sound(self, sound: str) -> None:
        file_name = _find(await self._sounds(), sound, "sound")
        await self._ask("playMeme", {"FileName": file_name, "IsKeyDown": True}, answered=False)

    async def stop_sounds(self) -> None:
        await self._ask("stopAllMemeSounds", {}, answered=False)

    async def toggle(self, switch: str) -> dict[str, bool]:
        action = TOGGLES.get(str(switch).strip())
        if action is None:
            raise ValueError(f"Which switch? One of {', '.join(TOGGLES)}")
        return {"on": bool((await self._ask(action, {})).get("value"))}

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
