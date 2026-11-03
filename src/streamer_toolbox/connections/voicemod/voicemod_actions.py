from streamer_toolbox.connections.voicemod.boxes.flip_voicemod_switch import FlipVoicemodSwitch
from streamer_toolbox.connections.voicemod.boxes.play_voicemod_sound import PlayVoicemodSound
from streamer_toolbox.connections.voicemod.boxes.random_voicemod_voice import RandomVoicemodVoice
from streamer_toolbox.connections.voicemod.boxes.set_voicemod_voice import SetVoicemodVoice
from streamer_toolbox.connections.voicemod.boxes.stop_voicemod_sounds import StopVoicemodSounds
from streamer_toolbox.connections.voicemod.boxes.voicemod_box import Ask
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class VoicemodActions:
    """Voicemod's boxes, over its Control API (control-api.voicemod.net): switch the voice, play a
    soundboard sound, flip one of its switches. Voices and sounds are picked by name (the pickers list them
    from the running program); the id is looked up.

    One Box class per box, in boxes/."""

    def __init__(self, ask: Ask) -> None:
        self._ask = ask

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (SetVoicemodVoice(self._ask), RandomVoicemodVoice(self._ask), PlayVoicemodSound(self._ask),
                    StopVoicemodSounds(self._ask), FlipVoicemodSwitch(self._ask)):
            actions.add_box(box, "voicemod")
