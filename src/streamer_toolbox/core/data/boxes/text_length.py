from streamer_toolbox.core.interfaces.box import Box


class TextLength(Box):
    name = "length"
    label = "Text length"
    help = "How many characters the text has"
    group = "Text"
    flow_only = True

    async def run(self, text: str) -> int:
        return len(str(text))
