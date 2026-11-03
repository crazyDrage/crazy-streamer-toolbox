from streamer_toolbox.connections.veadotube.boxes.veadotube_box import VeadotubeBox


class GetPushToTalk(VeadotubeBox):
    name = "get_push_to_talk"
    label = "Get push-to-talk"
    help = "Whether veadotube mini's push-to-talk (its microphone) is on"
    outputs = {"on": "yes/no"}

    async def run(self) -> dict[str, bool]:
        if self._client.talk is None:
            raise ConnectionError("veadotube mini is not connected, or it has no push-to-talk")
        return {"on": self._client.talk}
