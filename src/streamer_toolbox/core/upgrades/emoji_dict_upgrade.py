from collections.abc import Callable

from streamer_toolbox.core.upgrades.settings_upgrade import SettingsUpgrade


class EmojiDictUpgrade(SettingsUpgrade):
    """Settings version 6 (2026-11-16, docs/SETTINGS_CHANGES.md): the chat event type that came with the toolbox
    gets the value `emoji_dict` (his emoji dictionary: a text shows its words as pictures), so the Twitch chat
    flow can give it. A chat type he made himself, or one that has it, stays as it is. Flows don't change:
    "Add default flows" → "Update them" brings the new Twitch chat flow.

    `add_emoji_dict()` adds the value (EventTypeStore.add_values) and gives the names it added."""

    version = 6
    about = "emoji dictionary"

    def __init__(self, add_emoji_dict: Callable[[], list[str]]) -> None:
        self._add_emoji_dict = add_emoji_dict

    def run(self) -> list[str]:
        return ["the chat event got the value emoji_dict"] if self._add_emoji_dict() else []
