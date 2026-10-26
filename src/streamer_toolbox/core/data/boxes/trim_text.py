from streamer_toolbox.core.interfaces.box import Box


class TrimText(Box):
    name = "trim"
    label = "Trim text"
    help = "Takes away spaces (and line breaks) at the start and the end"
    group = "Text"
    flow_only = True

    async def run(self, text: str) -> str:
        return str(text).strip()
