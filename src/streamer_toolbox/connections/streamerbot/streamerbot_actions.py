import json
from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry

Ask = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]  # one request → Streamer.bot's answer
NOT_AN_OBJECT = 'The arguments must be an object like {"user": "ann"}'
PLATFORMS = ["twitch", "kick", "youtube"]


class StreamerbotActions:
    """Streamer.bot's boxes. What happens is built in Streamer.bot as an action; the toolbox runs it by name
    (the picker lists them from the running program) and can hand it arguments, which the action finds as
    %name%."""

    def __init__(self, ask: Ask) -> None:
        self._ask = ask

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("streamerbot.do_action", self.do_action, "Runs an action made in Streamer.bot",
                    "Run Streamer.bot action", options={"action": self.action_names},
                    hints={"args": 'Optional: an object like {"user": "ann"}; the action gets each as %user%'})
        actions.add("streamerbot.code_trigger", self.code_trigger, "Fires a custom trigger made in "
                    "Streamer.bot's C# code: every action with that trigger runs", "Fire Streamer.bot trigger",
                    hints={"trigger": "The trigger's name, exactly as registered in Streamer.bot",
                           "args": 'Optional: an object like {"user": "ann"}'})
        actions.add("streamerbot.get_global", self.get_global, "The value of one of Streamer.bot's global "
                    "variables", "Get Streamer.bot global", outputs={"value": "text"},
                    hints={"persisted": "Yes: a variable Streamer.bot keeps over a restart"})
        actions.add("streamerbot.send_chat", self.send_chat, "Writes in chat through Streamer.bot's own "
                    "accounts. Streamer.bot only allows it with a password set on its WebSocket server",
                    "Write in chat through Streamer.bot", options={"platform": self.platforms},
                    hints={"bot": "Yes: as Streamer.bot's bot account. No: as the streamer"})

    async def action_names(self) -> list[str]:
        try:
            answer = await self._ask({"request": "GetActions"})
        except ConnectionError:
            return []
        return sorted(str(a.get("name")) for a in answer.get("actions") or []
                      if isinstance(a, dict) and a.get("name") and a.get("enabled", True))

    @staticmethod
    async def platforms() -> list[str]:
        return list(PLATFORMS)

    async def do_action(self, action: str, args: Any = None) -> None:
        action = str(action).strip()
        if not action:
            raise ValueError("Which action? Pick one made in Streamer.bot")
        await self._ask({"request": "DoAction", "action": {"name": action}, "args": _object(args)})

    async def code_trigger(self, trigger: str, args: Any = None) -> None:
        trigger = str(trigger).strip()
        if not trigger:
            raise ValueError("Which trigger? It is the name the trigger was registered with in Streamer.bot")
        await self._ask({"request": "ExecuteCodeTrigger", "triggerName": trigger, "args": _object(args)})

    async def get_global(self, variable: str, persisted: bool = True) -> dict[str, Any]:
        answer = await self._ask({"request": "GetGlobal", "variable": str(variable).strip(),
                                  "persisted": bool(persisted)})
        found = answer.get("variable") if isinstance(answer.get("variable"), dict) else {}
        return {"value": found.get("value", "")}

    async def send_chat(self, message: str, platform: str = "twitch", bot: bool = True) -> None:
        platform = str(platform).strip().casefold()
        if platform not in PLATFORMS:
            raise ValueError(f"Streamer.bot writes on {', '.join(PLATFORMS)}; not on {platform!r}")
        if not str(message).strip():
            raise ValueError("What should be written?")
        await self._ask({"request": "SendMessage", "platform": platform, "bot": bool(bot), "internal": False,
                         "message": str(message)})


def _object(values: Any) -> dict[str, Any]:
    if values in (None, ""):
        return {}
    if isinstance(values, str):
        try:
            values = json.loads(values)
        except ValueError:
            raise ValueError(NOT_AN_OBJECT) from None
    if not isinstance(values, dict):
        raise ValueError(NOT_AN_OBJECT)
    return {str(key): value for key, value in values.items()}
