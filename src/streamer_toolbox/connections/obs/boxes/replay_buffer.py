from streamer_toolbox.connections.obs.boxes.obs_output_box import ObsOutputBox, REPLAY, _choices, _request


class ReplayBuffer(ObsOutputBox):
    name = "replay_buffer"
    label = "Replay buffer"
    help = "Saves the replay buffer as a clip (the last seconds it keeps; set under Settings → Output → Replay " \
           "Buffer), or starts / stops it"
    options = {"action": _choices(REPLAY)}
    group = "Recording / streaming"

    async def run(self, action: str = "save") -> None:
        await self._requests(_request(REPLAY, action))
