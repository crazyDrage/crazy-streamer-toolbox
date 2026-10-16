from collections.abc import Awaitable, Callable

Step = Callable[[], Awaitable[None] | None]


class StartOnce:
    """What starts the toolbox's work (the connections, the timers, the background loads), run once: at the
    server's start when nothing is locked, or after the login (Settings → Login) when the secrets are."""

    def __init__(self, steps: list[Step]) -> None:
        self._steps = steps
        self.started = False

    async def run(self) -> None:
        if self.started:
            return
        self.started = True
        for step in self._steps:
            result = step()
            if result is not None:
                await result
