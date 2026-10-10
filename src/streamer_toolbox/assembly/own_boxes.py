from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.json_actions import JsonActions
from streamer_toolbox.core.data.list_actions import ListActions
from streamer_toolbox.core.data.object_actions import ObjectActions
from streamer_toolbox.core.data.split_actions import SplitActions
from streamer_toolbox.core.data.text_actions import TextActions
from streamer_toolbox.core.files.file_actions import FileActions
from streamer_toolbox.core.interfaces.confirm_service import ConfirmService
from streamer_toolbox.core.interfaces.message_service import MessageService
from streamer_toolbox.core.media.miniaudio_sound_player import MiniaudioSoundPlayer
from streamer_toolbox.core.media.mp4_header_probe import Mp4HeaderProbe
from streamer_toolbox.core.media.sound_actions import SoundActions
from streamer_toolbox.core.media.video_actions import VideoActions
from streamer_toolbox.core.popups.popup_actions import PopupActions
from streamer_toolbox.core.system.program_actions import ProgramActions
from streamer_toolbox.core.system.time_actions import TimeActions
from streamer_toolbox.core.variables.variable_store import VariableStore
from streamer_toolbox.core.variables.viewer_actions import ViewerActions
from streamer_toolbox.core.web.http_actions import HttpActions


class OwnBoxes:
    """The boxes that belong to no program: text files, lists, JSON, Split data, objects, text, web requests,
    running a program, per-viewer values, time, popups, video info and sound. (The logic boxes are LogicActions,
    the ones for flows, alerts, widgets, tips and points are added where those are made, in assemble().)"""

    def __init__(self, variables: VariableStore, probe: Mp4HeaderProbe, messages: MessageService,
                 confirm: ConfirmService, sound_folder: str | None) -> None:
        self._variables = variables
        self._probe = probe
        self._messages = messages
        self._confirm = confirm
        self._sound_folder = sound_folder

    def add_to(self, actions: ActionRegistry) -> None:
        FileActions().add_to(actions)
        ListActions(self._variables).add_to(actions)
        JsonActions().add_to(actions)
        SplitActions().add_to(actions)
        ObjectActions().add_to(actions)
        TextActions().add_to(actions)
        HttpActions().add_to(actions)
        ProgramActions().add_to(actions)
        ViewerActions(self._variables).add_to(actions)
        TimeActions().add_to(actions)
        PopupActions(self._messages, self._confirm).add_to(actions)
        VideoActions(self._probe).add_to(actions)
        SoundActions(MiniaudioSoundPlayer(),
                     Path(self._sound_folder) if self._sound_folder else None).add_to(actions)
