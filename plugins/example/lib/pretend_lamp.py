import asyncio

COLORS = {"white": "#f5f5f5", "red": "#e53935", "green": "#43a047", "blue": "#1e88e5", "purple": "#8e24aa"}


class PretendLamp:
    """Stands in for a real program, so the example runs with nothing installed.

    In a real plugin this class is the part that talks to the program: it would hold a websocket or send web
    requests (look at `src/streamer_toolbox/connections/firebot_connection.py` for web requests, and
    `connections/websocket/request_socket.py` for a websocket that stays open). Everything else in this
    plugin would stay the same.

    It knows nothing about the toolbox. That is on purpose: the class that talks to a program and the classes
    that plug it into the toolbox (LampConnection, LampActions) are kept apart, so each can be read alone."""

    def __init__(self) -> None:
        self.on = False
        self.color = "white"
        self.blinks = 0  # how often it has blinked since the toolbox started

    def switch(self, on: bool) -> None:
        self.on = bool(on)

    def set_color(self, color: str) -> str:
        """Changes the colour and gives back the one it had before."""
        if color not in COLORS:
            raise ValueError(f"The lamp has no colour {color!r}. It has: {', '.join(COLORS)}")
        before, self.color = self.color, color
        return before

    async def blink(self, times: int, seconds: float) -> None:
        """Off and on again, `times` times. It takes real time, like a real lamp would: that is why it is
        `async` and uses `asyncio.sleep`. Never use `time.sleep` in a plugin: it freezes the whole toolbox."""
        was_on = self.on
        for _ in range(times):
            self.on = False
            await asyncio.sleep(seconds)
            self.on = True
            await asyncio.sleep(seconds)
        self.on = was_on
        self.blinks += 1
