from typing import Any

from streamer_toolbox.connections.twitch.boxes.twitch_stream_box import (TwitchStreamBox, PREDICTION_ENDS, _first,
                                                                         _prediction_ends)


class EndPrediction(TwitchStreamBox):
    name = "end_prediction"
    label = "End prediction"
    help = "Ends the running prediction: winner = that outcome won (points are paid out), cancel = everyone gets " \
           "the points back, lock = no more bets"
    options = {"how": _prediction_ends}
    hints = {"winner": "the outcome's title, for how = winner"}
    group = "Polls and predictions"

    async def run(self, how: str = "winner", winner: str = "") -> None:
        self._allowed("channel:manage:predictions")
        if how not in PREDICTION_ENDS:
            raise ValueError(f"how is one of {', '.join(PREDICTION_ENDS)}")
        me = self._me().user_id
        prediction = _first(await self._helix("GET", "predictions", params={"broadcaster_id": me, "first": 1}))
        if prediction.get("status") not in ("ACTIVE", "LOCKED"):
            raise RuntimeError("no prediction is running")
        change: dict[str, Any] = {"broadcaster_id": me, "id": prediction["id"],
                                  "status": {"winner": "RESOLVED", "cancel": "CANCELED", "lock": "LOCKED"}[how]}
        if how == "winner":
            wanted = str(winner).strip().casefold()
            found = next((o for o in prediction.get("outcomes") or []
                          if str(o.get("title", "")).casefold() == wanted), None)
            if found is None:
                titles = ", ".join(str(o.get("title", "")) for o in prediction.get("outcomes") or [])
                raise LookupError(f"the prediction has no outcome {winner!r} (it has: {titles})")
            change["winning_outcome_id"] = found["id"]
        await self._helix("PATCH", "predictions", json=change)
