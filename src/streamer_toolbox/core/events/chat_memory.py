from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.events.boxes.chat_memory_shared import KEPT
from streamer_toolbox.core.events.boxes.get_chat_message import GetChatMessage


class ChatMemory:
    """The last chat messages, by their id, for the box "Get chat message". No platform has a request for
    "the text of message X", and "Chat message deleted" only says which id went: so the toolbox remembers
    what came through chat itself (in memory only, the newest 1000, since it started) and the box looks it up.

    Listens to the common `chat` event, so it works for every platform whose chat gives message ids."""

    def __init__(self, kept: int = KEPT) -> None:
        self._kept = kept
        self._messages: dict[str, dict[str, Any]] = {}

    async def handle(self, kind: str, data: dict[str, Any]) -> None:
        message_id = str(data.get("message_id") or "") if kind == "chat" else ""
        if not message_id:
            return
        self._messages[message_id] = {key: data.get(key, "") for key in ("message", "user", "user_id", "role",
                                                                         "platform")}
        while len(self._messages) > self._kept:
            del self._messages[next(iter(self._messages))]

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (GetChatMessage(self),):
            actions.add_box(box, "viewer")

    async def get(self, message_id: str) -> dict[str, Any]:
        known = self._messages.get(str(message_id if message_id is not None else "").strip())
        return {"found": known is not None,
                **(known or {"message": "", "user": "", "user_id": "", "role": "", "platform": ""})}
