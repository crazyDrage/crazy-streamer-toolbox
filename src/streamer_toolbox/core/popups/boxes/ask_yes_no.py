from streamer_toolbox.core.popups.boxes.popup_box import PopupBox, ANSWERS


class AskYesNo(PopupBox):
    name = "ask"
    label = "Ask yes/no"
    help = "Asks a yes/no question on every open toolbox screen; the first answer picks the way on. 'no_answer' " \
           "if nobody answers in time or no toolbox screen is open"
    group = "Popups"
    ports = tuple(ANSWERS.values())
    flow_only = True

    async def run(self, question: str, seconds: float = 20) -> str:
        return ANSWERS[await self._confirm.ask(str(question), float(seconds))]
