from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.upgrades.settings_upgrade import SettingsUpgrade

PICTURE = "twitch.profile_picture"
OLD_FIELD, NEW_FIELD, GONE_FIELD = "user", "user_id", "platform"
SEND_CHAT, KEEP, REMEMBER = "event.send.chat", "media.keep_locally", "cache.value"
# the chat flow v0.5.0-dev.5 to dev.7 made: Start → picture (with its platform field) → keep → Send
OLD_CHAT_WIRES = {FlowWire("t1", "out", "n2"), FlowWire("n2", "done", "n3"), FlowWire("n3", "done", "n1")}


class ProfilePictureUpgrade(SettingsUpgrade):
    """Settings version 5 (2026-11-15, his round 90, docs/SETTINGS_CHANGES.md): the box Twitch profile picture's
    field `user` is `user_id`, and its `platform` field is gone (only Twitch; the platform check is an If on the
    flow, rule 29). The chat flow the toolbox made in dev.5 to dev.7, unchanged, is made new in its new shape
    (split: Event: chat for every other platform, Event: chat · Twitch with the picture; `rebuild_chat()`,
    EventFlows.update_default; a chat
    type without the picture value would make it without the boxes, so then it stays and only the field changes). The
    picture box's own cache (cache/twitch_pictures.json) is gone: Remembered value keeps the addresses now."""

    version = 5
    about = "Twitch profile picture"

    def __init__(self, flows: FlowLibrary, rebuild_chat: Callable[[], str], old_cache: Path) -> None:
        self._flows = flows
        self._rebuild_chat = rebuild_chat
        self._old_cache = old_cache

    def run(self) -> list[str]:
        said = []
        for flow in self._flows.all():
            if _old_chat_flow(flow):
                self._rebuild_chat()
                if any(node.action == REMEMBER for made in self._flows.all() for node in made.nodes):
                    said.append(f"flow {flow.label!r}: made new, with \"Event: chat · Twitch\" for Twitch's chat "
                                "(Remembered value → Twitch profile picture)")
                    continue
                self._flows.save(flow, flow.name)  # a chat type without its picture value: the boxes stay
            changed = self.flow(flow)
            if changed != flow:
                self._flows.save(changed, flow.name)
                said.append(f"flow {flow.label!r}: Twitch profile picture's user is user_id now")
            if any(node.action == PICTURE and str(node.params.get(GONE_FIELD) or "").strip() for node in flow.nodes):
                said.append(f"flow {flow.label!r}: Twitch profile picture had a platform field and now asks Twitch "
                            "for everyone: put an If (platform is twitch) before it")
        if self._old_cache.is_file():
            self._old_cache.unlink()
            said.append(f"{self._old_cache.name} is gone (Remembered value keeps the addresses now)")
        return said

    def flow(self, flow: Flow) -> Flow:
        if not any(node.action == PICTURE and (OLD_FIELD in node.params or GONE_FIELD in node.params)
                   for node in flow.nodes):
            return flow
        return replace(flow, nodes=tuple(replace(node, params=_new_fields(node.params)) if node.action == PICTURE
                                         else node for node in flow.nodes))


def _new_fields(params: dict) -> dict:
    return {(NEW_FIELD if key == OLD_FIELD else key): value for key, value in params.items()
            if key != GONE_FIELD and not (key == OLD_FIELD and NEW_FIELD in params)}


def _old_chat_flow(flow: Flow) -> bool:
    """The chat flow as dev.5 to dev.7 made it, not changed by hand."""
    by_id = {node.id: node for node in flow.nodes}
    return (set(by_id) == {"n1", "n2", "n3"} and by_id["n1"].action == SEND_CHAT and by_id["n3"].action == KEEP
            and by_id["n2"].action == PICTURE and GONE_FIELD in by_id["n2"].params
            and set(flow.wires) == OLD_CHAT_WIRES)
