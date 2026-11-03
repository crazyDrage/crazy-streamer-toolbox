from streamer_toolbox.core.interfaces.box import Box


class SplitText(Box):
    name = "split"
    data_only = True  # no run wire: only works out a value from its inputs (his rule, round 62 A / notes 10-29)
    label = "Split text"
    help = "Cuts text into a list at each separator (empty = at spaces), e.g. a redeem message 'll 5' → ['ll', " \
           "'5']. Empty pieces are left out"
    group = "Text"
    flow_only = True

    async def run(self, text: str, separator: str = "") -> list[str]:
        parts = str(text).split(separator) if separator else str(text).split()
        return [p.strip() for p in parts if p.strip()]
