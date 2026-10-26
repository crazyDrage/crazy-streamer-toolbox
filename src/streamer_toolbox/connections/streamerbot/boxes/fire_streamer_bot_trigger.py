from typing import Any

from streamer_toolbox.connections.streamerbot.boxes.streamerbot_box import StreamerbotBox, _object


class FireStreamerBotTrigger(StreamerbotBox):
    name = "code_trigger"
    label = "Fire Streamer.bot trigger"
    help = "Fires a custom trigger made in Streamer.bot's C# code: every action with that trigger runs"
    hints = {"trigger": "The trigger's name, exactly as registered in Streamer.bot. Streamer.bot "
                        "doesn't say when no trigger has that name: then nothing happens",
             "args": 'Optional: an object like {"user": "ann"}'}

    async def run(self, trigger: str, args: Any = None) -> None:
        trigger = str(trigger).strip()
        if not trigger:
            raise ValueError("Which trigger? It is the name the trigger was registered with in Streamer.bot")
        await self._ask({"request": "ExecuteCodeTrigger", "triggerName": trigger, "args": _object(args)})
