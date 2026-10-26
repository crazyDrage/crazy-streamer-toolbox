from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.boxes.change_case import ChangeCase
from streamer_toolbox.core.data.boxes.join_list_to_text import JoinListToText
from streamer_toolbox.core.data.boxes.replace_in_text import ReplaceInText
from streamer_toolbox.core.data.boxes.split_text import SplitText
from streamer_toolbox.core.data.boxes.text_length import TextLength
from streamer_toolbox.core.data.boxes.trim_text import TrimText


class TextActions:
    """Text boxes (SAMMI's String commands): split a chat message into words, join, replace, length, case.

    One Box class per box, in boxes/."""

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (SplitText(), JoinListToText(), ReplaceInText(), TextLength(), ChangeCase(), TrimText()):
            actions.add_box(box, "text")
