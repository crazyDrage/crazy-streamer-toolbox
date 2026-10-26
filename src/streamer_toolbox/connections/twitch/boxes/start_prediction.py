from typing import Any

from streamer_toolbox.connections.twitch.boxes.twitch_stream_box import TwitchStreamBox, _first, _title, _titles


class StartPrediction(TwitchStreamBox):
    name = "start_prediction"
    label = "Start prediction"
    help = "Starts a prediction; gives its id"
    hints = {"outcomes": "2 to 10, separated by commas (or a list)",
             "seconds": "30 to 1800"}
    group = "Polls and predictions"

    async def run(self, title: str, outcomes: Any, seconds: int = 120) -> str:
        self._allowed("channel:manage:predictions")
        titles = _titles(outcomes, 2, 10, "outcomes")
        prediction = _first(await self._helix("POST", "predictions", json={
            "broadcaster_id": self._me().user_id, "title": _title(title, 45),
            "outcomes": [{"title": t[:25]} for t in titles],
            "prediction_window": max(30, min(int(seconds), 1800))}))
        return prediction.get("id", "")
