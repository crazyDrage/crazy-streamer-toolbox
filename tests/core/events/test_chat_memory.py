import unittest

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.events.chat_memory import ChatMemory


def chat(message_id: str, message: str) -> dict:
    return {"user": "Kit", "user_id": "77", "message": message, "message_id": message_id, "role": "vip",
            "platform": "twitch", "source": "twitch.chat"}


class TestChatMemory(unittest.IsolatedAsyncioTestCase):
    async def test_a_deleted_messages_text_is_found_by_its_id(self) -> None:
        memory, actions = ChatMemory(), ActionRegistry()
        memory.add_to(actions)
        await memory.handle("chat", chat("m1", "hello lizard"))
        await memory.handle("twitch.chat", chat("m2", "the platform's own event is not kept twice"))
        await memory.handle("chat", {"user": "Ann", "message": "no id (Rumble)", "platform": "rumble"})
        self.assertEqual(await actions.run("viewer.chat_message", message_id=" m1 "), {
            "found": True, "message": "hello lizard", "user": "Kit", "user_id": "77", "role": "vip",
            "platform": "twitch"})
        for unknown in ("m2", "", None):
            self.assertEqual(await actions.run("viewer.chat_message", message_id=unknown), {
                "found": False, "message": "", "user": "", "user_id": "", "role": "", "platform": ""})

    async def test_only_the_newest_are_kept(self) -> None:
        memory = ChatMemory(kept=3)
        for number in range(5):
            await memory.handle("chat", chat(f"m{number}", f"text {number}"))
        self.assertEqual([(await memory.get(f"m{n}"))["found"] for n in range(5)], [False, False, True, True, True])


if __name__ == "__main__":
    unittest.main()
