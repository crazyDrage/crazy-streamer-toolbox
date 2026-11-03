from streamer_toolbox.core.interfaces.box import Box


class WaitForAll(Box):
    name = "wait_for_all"
    label = "Wait for all"
    help = "Goes on once every box wired into it is done, e.g. after boxes that run at the same time. Not after an " \
           "If: only one of its sides ever arrives"
    group = "Wait"
    flow_only = True
    join = True

    async def run(self) -> None:
        """Does nothing itself; the FlowRunner holds it back until all its wires arrived."""
