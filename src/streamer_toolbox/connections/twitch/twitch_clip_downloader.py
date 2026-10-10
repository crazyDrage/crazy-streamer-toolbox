import asyncio
import os
import platform
from collections.abc import Awaitable, Callable
from pathlib import Path

from streamer_toolbox.connections.twitch.twitch_clip_files import clip_id
from streamer_toolbox.core.system.github_program import GithubProgram

REPO = "lay295/TwitchDownloader"  # MIT; the toolbox doesn't ship it, each PC gets it from the project itself
RunProgram = Callable[[list[str], float], Awaitable[tuple[int, str]]]  # (command, seconds) → (exit code, text)


class TwitchClipDownloader:
    """Downloads a clip as a file with TwitchDownloaderCLI (github.com/lay295/TwitchDownloader), the program
    his own clip tool used. The toolbox gets that program from the project's GitHub releases and keeps it up
    to date (GithubProgram), so when Twitch changes something, the project's fix arrives by itself.

    A clip is downloaded once: its file stays in the clips folder (the newest `keep` of them) and is given
    again when the same clip is asked for. The other way to play a clip, with no file at all, is
    TwitchClipFiles (Clip video address); this one is for when a file is wanted, or as the way back if that
    stops working."""

    def __init__(self, program: GithubProgram, folder: Path, run: RunProgram | None = None, keep: int = 20,
                 seconds: float = 180.0) -> None:
        self._program = program
        self._folder = folder
        self._run = run or run_program
        self._keep = keep
        self._seconds = seconds

    @property
    def version(self) -> str:
        return self._program.version

    async def update(self) -> dict:
        return await self._program.update()

    async def download(self, clip: str, quality: str = "") -> Path:
        """The clip's file (its id or link; quality like "720", "" = the best), downloaded if it isn't there."""
        slug = clip_id(clip)
        if not slug or any(sign in slug for sign in "\\:*?\"<>|"):
            raise ValueError(f"which clip? ({clip!r} is not a clip's id or link)")
        height = str(quality).strip().casefold().removesuffix("p")
        if height in ("", "best"):
            height = ""
        elif not height.isdigit():
            raise ValueError(f"quality is best, 1080, 720, 480 or 360, not {quality!r}")
        file = self._folder / f"{slug}{'_' + height if height else ''}.mp4"
        if file.is_file() and file.stat().st_size > 0:
            file.touch()  # used again: it counts as new for what is kept
            return file
        program = await self._program.path()
        self._folder.mkdir(parents=True, exist_ok=True)
        command = [str(program), "clipdownload", "-u", slug, "-o", str(file), "--collision", "Overwrite",
                   "--encode-metadata", "false", "--banner", "false", *(["-q", f"{height}p"] if height else [])]
        code, said = await self._run(command, self._seconds)
        if code != 0 or not file.is_file() or file.stat().st_size == 0:
            file.unlink(missing_ok=True)
            raise RuntimeError(f"the clip {slug} could not be downloaded ({_reason(said) or f'exit code {code}'}). "
                               "Deleted or private? If no clip downloads any more: Update clip downloader")
        self._forget_old()
        return file

    def _forget_old(self) -> None:
        files = sorted(self._folder.glob("*.mp4"), key=lambda one: one.stat().st_mtime, reverse=True)
        for old in files[self._keep:]:
            old.unlink(missing_ok=True)


def release_file(system: str = "", machine: str = "") -> Callable[[str], bool]:
    """Says which file of a TwitchDownloader release is the command line program for this system
    (TwitchDownloaderCLI-1.56.5-Windows-x64.zip, ...-Linux-x64.zip, ...-LinuxArm64.zip, ...)."""
    system = (system or platform.system()).casefold()
    arm = (machine or platform.machine()).casefold() in ("arm64", "aarch64")
    ending = {"windows": "-Windows-x64.zip", "linux": "-LinuxArm64.zip" if arm else "-Linux-x64.zip",
              "darwin": "-MacOSArm64.zip" if arm else "-MacOS-x64.zip"}.get(system, "-Linux-x64.zip")
    return lambda name: name.startswith("TwitchDownloaderCLI-") and name.endswith(ending)


def program_name(system: str = "") -> str:
    return "TwitchDownloaderCLI.exe" if (system or platform.system()).casefold() == "windows" else "TwitchDownloaderCLI"


def _reason(said: str) -> str:
    """The line of the program's output that says what went wrong: its own error line, or the first line of a
    crash (the lines after that are where in its code)."""
    lines = [line.strip() for line in said.splitlines() if line.strip()]
    told = [line for line in lines if not line.startswith(("at ", "--->", "[STATUS]"))]
    errors = [line for line in told if line.startswith("[ERROR]")]
    crashes = [line for line in told if "exception" in line.casefold()]
    return (errors[:1] or crashes[:1] or [" ".join(told[:2])])[0][:200]


async def run_program(command: list[str], seconds: float) -> tuple[int, str]:
    """Runs it to the end without a window; gives its exit code and what it printed."""
    # a .NET program stops on a Linux without the ICU library unless it is told to do without (seen on a bare
    # Debian); for a downloader that changes nothing
    env = {**os.environ, "DOTNET_SYSTEM_GLOBALIZATION_INVARIANT": "1"} if os.name != "nt" else None
    process = await asyncio.create_subprocess_exec(
        *command, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT, env=env)
    try:
        async with asyncio.timeout(seconds):
            out, _ = await process.communicate()
    except TimeoutError:
        process.kill()
        await process.wait()
        return 1, f"it didn't finish within {seconds:g} s"
    return process.returncode or 0, out.decode("utf-8", errors="replace")
