from streamer_toolbox.connections.streamerbot.boxes.fire_streamer_bot_trigger import FireStreamerBotTrigger
from streamer_toolbox.connections.streamerbot.boxes.get_streamer_bot_global import GetStreamerBotGlobal
from streamer_toolbox.connections.streamerbot.boxes.run_streamer_bot_action import RunStreamerBotAction
from streamer_toolbox.connections.streamerbot.boxes.streamerbot_box import Ask
from streamer_toolbox.connections.streamerbot.boxes.write_in_chat_through_streamer_bot import WriteInChatThroughStreamerBot
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class StreamerbotActions:
    """Streamer.bot's boxes. What happens is built in Streamer.bot as an action; the toolbox runs it by name
    (the picker lists them from the running program) and can hand it arguments, which the action finds as
    %name%.

    One Box class per box, in boxes/."""

    def __init__(self, ask: Ask) -> None:
        self._ask = ask

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (RunStreamerBotAction(self._ask), FireStreamerBotTrigger(self._ask),
                    GetStreamerBotGlobal(self._ask), WriteInChatThroughStreamerBot(self._ask)):
            actions.add_box(box, "streamerbot")
