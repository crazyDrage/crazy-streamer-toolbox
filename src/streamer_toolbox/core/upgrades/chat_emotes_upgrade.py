from collections.abc import Callable
from dataclasses import replace

from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.upgrades.settings_upgrade import SettingsUpgrade

SEND_CHAT, OLD, NEW = "event.send.chat", "emotes", "emoji_dict"


class ChatEmotesUpgrade(SettingsUpgrade):
    """Settings version 7 (2026-11-16, docs/SETTINGS_CHANGES.md), his "we don't need emotes and emoji_dict.
    remove the old one": the chat event type that came with the toolbox loses the value `emotes` (Twitch's list
    of a message's emotes); `emoji_dict` took its place. Each Send chat box loses its field `emotes`; one that
    gave the emoji dictionary there (a wire from an emoji_dict, his own flow did) gives it as `emoji_dict`.
    Imported StreamElements chat widgets get their emotes from emoji_dict (widget_events.dict_emotes).

    `remove_emotes()` takes the value out of the chat type (EventTypeStore.remove_values) and gives the names it
    took out."""

    version = 7
    about = "chat emotes into emoji_dict"

    def __init__(self, flows: FlowLibrary, remove_emotes: Callable[[], list[str]]) -> None:
        self._flows = flows
        self._remove_emotes = remove_emotes

    def run(self) -> list[str]:
        said = ["the chat event's value emotes is gone (emoji_dict has the emotes)"] if self._remove_emotes() else []
        for flow in self._flows.all():
            changed = self.flow(flow)
            if changed != flow:
                self._flows.save(changed, flow.name)
                said.append(f"{flow.label}: Send chat without emotes")
        return said

    def flow(self, flow: Flow) -> Flow:
        nodes = tuple(replace(node, params=_without_emotes(node.params)) if node.action == SEND_CHAT
                      and OLD in node.params else node for node in flow.nodes)
        return replace(flow, nodes=nodes) if nodes != flow.nodes else flow


def _without_emotes(params: dict) -> dict:
    """The fields without `emotes`; an emoji dictionary given there goes to emoji_dict (when that has none)."""
    given = params[OLD]
    kept = {key: value for key, value in params.items() if key != OLD}
    if f".{NEW}" in str(given) and not kept.get(NEW):
        kept[NEW] = given
    return kept
