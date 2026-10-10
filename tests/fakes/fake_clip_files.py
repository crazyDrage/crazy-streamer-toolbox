from typing import Any


class FakeClipFiles:
    """TwitchClipFiles from a list: every clip has these qualities, at https://cdn.test/<clip id>/<quality>.mp4.
    `asked` keeps the clips, `finder` whether the question finder was allowed each time."""

    def __init__(self, qualities: tuple[int, ...] = (1080, 720, 360)) -> None:
        self.qualities = qualities
        self.asked: list[str] = []
        self.finder: list[bool] = []

    async def files(self, clip: str, finder: bool = True) -> list[dict[str, Any]]:
        self.asked.append(clip)
        self.finder.append(finder)
        return [{"quality": q, "address": f"https://cdn.test/{clip}/{q}.mp4"} for q in self.qualities]
