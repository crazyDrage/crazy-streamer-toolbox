from pathlib import Path


class FakeClipDownloader:
    """TwitchClipDownloader without TwitchDownloaderCLI: every clip "downloads" to clips/<clip id>.mp4 at once.
    `asked` keeps (clip, quality) of each download."""

    def __init__(self) -> None:
        self.asked: list[tuple[str, str]] = []

    async def download(self, clip: str, quality: str = "") -> Path:
        self.asked.append((clip, quality))
        return Path("clips") / f"{clip}.mp4"

    async def update(self) -> dict:
        return {"version": "1.0", "updated": False}
