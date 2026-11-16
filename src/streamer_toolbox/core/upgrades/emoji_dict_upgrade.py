from collections.abc import Callable

from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.upgrades.settings_upgrade import SettingsUpgrade

SEND_CHAT, CHAT_TRIGGER = "event.send.chat", "chat"
HELPER_LABEL = "Twitch pfp and chat emotes"


class EmojiDictUpgrade(SettingsUpgrade):
    """Settings version 6 (2026-11-16, docs/SETTINGS_CHANGES.md): the chat event type that came with the toolbox
    gets the values `picture` (when it has none: settings from v0.4.1 and before never got it) and `emoji_dict`
    (his emoji dictionary). A chat type he made himself, or one that has them, stays as it is.

    Then the chat flows the toolbox made and nobody changed are made new (`rebuild_chat()`,
    EventFlows.update_default), so the picture and the emotes reach the widgets (his "the settings files of the
    last version may need to be converted into the current settings"; found by starting this version on settings
    v0.4.1 and v0.5.0-dev.6 / dev.7 made):
    - v0.4.1's Event: chat as it made it: its chat Start box straight into Send chat, each value from the field of
      the same name;
    - Event: chat · Twitch as step 5 made it a moment before from dev.5 to dev.7's flow: Start → the box "Twitch
      pfp and chat emotes" → Send chat, whose Send had no emoji_dict yet (the value only comes now).
    A flow changed by hand stays.

    `add_values()` adds the values (EventTypeStore.add_values) and gives the names it added."""

    version = 6
    about = "emoji dictionary"

    def __init__(self, add_values: Callable[[], list[str]], flows: FlowLibrary | None = None,
                 rebuild_chat: Callable[[], str] | None = None) -> None:
        self._add_values = add_values
        self._flows = flows
        self._rebuild_chat = rebuild_chat

    def run(self) -> list[str]:
        said = [f"the chat event got the value {name}" for name in self._add_values()]
        if self._flows is None or self._rebuild_chat is None:
            return said
        made = [flow for flow in self._flows.all() if _plain_chat_flow(flow) or self._twitch_without_emoji(flow)]
        if made:
            self._rebuild_chat()
            said += [f"flow {flow.label!r}: made new (the picture and the emotes)" for flow in made]
        return said

    def _twitch_without_emoji(self, flow: Flow) -> bool:
        """Event: chat · Twitch as step 5 made it: Start → the helper flow's box → Send chat without emoji_dict."""
        by_id = {node.id: node for node in flow.nodes}
        if set(by_id) != {"n1", "n2"} or by_id["n1"].action != SEND_CHAT or "emoji_dict" in by_id["n1"].params:
            return False
        helper = self._flows.get(by_id["n2"].action.removeprefix("flow.")) \
            if by_id["n2"].action.startswith("flow.") else None
        return (helper is not None and helper.label == HELPER_LABEL
                and set(flow.wires) == {FlowWire("t1", "out", "n2"), FlowWire("n2", "done", "n1")})


def _plain_chat_flow(flow: Flow) -> bool:
    """Event: chat as v0.4.1 (and the versions before) made it, unchanged: the chat Start box t1 into Send chat,
    every field the Start box's of the same name."""
    if len(flow.nodes) != 1 or len(flow.triggers) != 1:
        return False
    send, trigger = flow.nodes[0], flow.triggers[0]
    return (send.action == SEND_CHAT and trigger.kind == CHAT_TRIGGER and trigger.id == "t1" and not trigger.match
            and set(flow.wires) == {FlowWire("t1", "out", send.id)} and bool(send.params)
            and all(value == f"${{box.t1.{key}}}" for key, value in send.params.items()))
