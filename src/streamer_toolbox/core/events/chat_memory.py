from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry

KEPT = 1000  # chat messages remembered, the newest ones


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
        actions.add("viewer.chat_message", self.get, "The text of a chat message by its id, e.g. the one that "
                    "\"Chat message deleted\" names. From the toolbox's own memory (the newest 1000 messages since it "
                    "started), no request to the platform; found = no when it doesn't know the id",
                    "Get chat message", group="Chat",
                    outputs={"found": "yes/no", "message": "text", "user": "text", "user_id": "text",
                             "role": "text", "platform": "text"},
                    hints={"message_id": "Wire the trigger's message_id into it"})

    async def get(self, message_id: str) -> dict[str, Any]:
        known = self._messages.get(str(message_id if message_id is not None else "").strip())
        return {"found": known is not None,
                **(known or {"message": "", "user": "", "user_id": "", "role": "", "platform": ""})}
