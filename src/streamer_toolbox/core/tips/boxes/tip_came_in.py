from typing import Any

from streamer_toolbox.core.tips.boxes.tip_box import TipBox, TIP


class TipCameIn(TipBox):
    name = "fire"
    label = "Tip came in"
    help = "Tells the toolbox a tip / donation came in: flows with a Tip trigger start, the Tip alert shows, " \
           "widgets get it as tip-latest. For services the toolbox has no connection to: call it from a flow or " \
           "over the API"
    group = "Tips"
    hints = {"amount": "e.g. 5 or 4.99", "currency": "e.g. EUR, USD (shown in alerts)",
             "source": "where it came from, e.g. streamelements, kofi (any word; flows can check it "
                       "as platform)"}

    async def run(self, user: str, amount: float, currency: str = "", message: str = "",
                  source: str = "") -> dict[str, Any]:
        try:
            value = round(float(amount), 2)
        except (TypeError, ValueError):
            raise ValueError(f"amount must be a number like 5 or 4.99, not {amount!r}") from None
        if value <= 0:
            raise ValueError(f"a tip's amount must be above 0, got {value:g}")
        tip = {"user": str(user).strip(), "amount": int(value) if value == int(value) else value,
               "currency": str(currency).strip().upper(), "message": str(message), "platform": str(source).strip()}
        self._events.publish(TIP, tip)
        return tip
