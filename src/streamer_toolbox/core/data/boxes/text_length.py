from streamer_toolbox.core.interfaces.box import Box


class TextLength(Box):
    name = "length"
    data_only = True  # no run wire: only works out a value from its inputs (his rule, round 62 A / notes 10-29)
    label = "Text length"
    help = "How many characters the text has"
    group = "Text"
    flow_only = True

    async def run(self, text: str) -> int:
        return len(str(text))
