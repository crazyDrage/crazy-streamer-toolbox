from typing import TYPE_CHECKING, Any

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.core.events.chat_memory import ChatMemory


class GetChatMessage(Box):
    name = "chat_message"
    label = "Get chat message"
    help = 'The text of a chat message by its id, e.g. the one that "Chat message deleted" names. From the ' \
           "toolbox's own memory (the newest 1000 messages since it started), no request to the platform; found " \
           "= no when it doesn't know the id"
    group = "Chat"
    outputs = {"found": "yes/no", "message": "text", "user": "text", "user_id": "text",
               "role": "text", "platform": "text"}
    hints = {"message_id": "Wire the trigger's message_id into it"}

    def __init__(self, chat_memory: "ChatMemory") -> None:
        self._chat_memory = chat_memory

    async def run(self, message_id: str) -> dict[str, Any]:
        return await self._chat_memory.get(message_id)
