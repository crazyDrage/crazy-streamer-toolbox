from streamer_toolbox.core.popups.boxes.popup_box import PopupBox


class ShowMessage(PopupBox):
    name = "message"
    label = "Show message"
    help = "Shows a message on every open toolbox screen until OK is pressed; the flow goes on right away"
    group = "Popups"

    async def run(self, message: str, title: str = "") -> int:
        return await self._messages.show(str(message), str(title))
