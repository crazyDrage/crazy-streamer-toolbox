import os
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.connections.twitch.twitch_clip_actions import TwitchClipActions
from streamer_toolbox.connections.twitch.twitch_clip_downloader import (TwitchClipDownloader, program_name,
                                                                        release_file)
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from tests.fakes.fake_clip_files import FakeClipFiles
from tests.fakes.fake_github_program import FakeGithubProgram


class TestTwitchClipDownloader(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.clips = Path(self._dir.name) / "cache" / "clips"
        self.program = FakeGithubProgram(Path(self._dir.name) / "TwitchDownloaderCLI.exe", ("1.56.5", "1.57.0"))
        self.commands: list[list[str]] = []
        self.fails = ""
        self.downloader = TwitchClipDownloader(self.program, self.clips, self._run, keep=2)
        self.actions = ActionRegistry()
        TwitchClipActions(FakeClipFiles(), self.downloader).add_to(self.actions)

    def tearDown(self) -> None:
        self._dir.cleanup()

    async def _run(self, command: list[str], seconds: float) -> tuple[int, str]:
        self.commands.append(command)
        if self.fails:
            return 1, self.fails
        Path(command[command.index("-o") + 1]).write_bytes(b"video")
        return 0, "done"

    async def test_a_clip_is_downloaded_once_with_the_program_from_github(self) -> None:
        got = await self.actions.run("twitch.download_clip", clip="https://clips.twitch.tv/Abc-1")
        file = self.clips / "Abc-1.mp4"
        self.assertEqual(got, {"file": str(file), "id": "Abc-1"})
        self.assertEqual(self.commands, [[
            str(self.program.file), "clipdownload", "-u", "Abc-1", "-o", str(file), "--collision", "Overwrite",
            "--encode-metadata", "false", "--banner", "false"]])
        await self.actions.run("twitch.download_clip", clip="Abc-1")
        self.assertEqual((len(self.commands), self.program.asked), (1, 1))  # the file is there: nothing is started

    async def test_a_quality_is_passed_on_and_gets_a_file_of_its_own(self) -> None:
        got = await self.actions.run("twitch.download_clip", clip="Abc-1", quality="720p")
        self.assertEqual((Path(got["file"]).name, self.commands[0][-2:]), ("Abc-1_720.mp4", ["-q", "720p"]))
        with self.assertRaisesRegex(ValueError, "quality is best, 1080"):
            await self.actions.run("twitch.download_clip", clip="Abc-1", quality="sharp")
        with self.assertRaisesRegex(ValueError, "which clip"):
            await self.actions.run("twitch.download_clip", clip="  ")

    async def test_a_failed_download_says_what_the_program_said_and_leaves_no_file(self) -> None:
        self.fails = "[STATUS] - Fetching Clip Info\n[ERROR] - Clip not found\n   at Some.Code() in x.cs:line 1"
        with self.assertRaisesRegex(RuntimeError, r"Gone could not be downloaded \(\[ERROR\] - Clip not found\)"):
            await self.actions.run("twitch.download_clip", clip="Gone")
        self.fails = ("[STATUS] - Fetching Clip Info\nUnhandled exception. System.AggregateException: One or more "
                      "errors occurred.\n ---> System.NullReferenceException: x\n   at Some.Code() in x.cs:line 1")
        with self.assertRaisesRegex(RuntimeError, r"\(Unhandled exception\. System\.Aggregate.*\)\. Deleted"):
            await self.actions.run("twitch.download_clip", clip="Gone")
        self.assertEqual(list(self.clips.glob("*")), [])

    async def test_only_the_newest_files_are_kept(self) -> None:
        for number, clip in enumerate(("A", "B", "C")):
            file = Path((await self.actions.run("twitch.download_clip", clip=clip))["file"])
            os.utime(file, (1000 + number, 1000 + number))
        await self.actions.run("twitch.download_clip", clip="D")
        self.assertEqual(sorted(p.name for p in self.clips.glob("*")), ["C.mp4", "D.mp4"])

    async def test_update_asks_for_a_newer_program(self) -> None:
        self.assertEqual(await self.actions.run("twitch.update_clip_downloader"),
                         {"version": "1.56.5", "updated": True})
        self.assertEqual((await self.actions.run("twitch.update_clip_downloader"))["version"], "1.57.0")

    def test_the_release_file_for_each_system(self) -> None:
        names = [f"TwitchDownloaderCLI-1.56.5-{system}.zip" for system in (
            "Linux-x64", "LinuxAlpine-x64", "LinuxArm", "LinuxArm64", "MacOS-x64", "MacOSArm64", "Windows-x64")]
        names.append("TwitchDownloaderGUI-1.56.5-Windows-x64.zip")
        for system, machine, wanted in (("Windows", "AMD64", "Windows-x64"), ("Linux", "x86_64", "Linux-x64"),
                                        ("Linux", "aarch64", "LinuxArm64"), ("Darwin", "arm64", "MacOSArm64")):
            fits = [name for name in names if release_file(system, machine)(name)]
            self.assertEqual(fits, [f"TwitchDownloaderCLI-1.56.5-{wanted}.zip"], system)
        self.assertEqual((program_name("Windows"), program_name("Linux")),
                         ("TwitchDownloaderCLI.exe", "TwitchDownloaderCLI"))

    def test_without_a_settings_folder_there_is_no_download_box(self) -> None:
        actions = ActionRegistry()
        TwitchClipActions(FakeClipFiles()).add_to(actions)
        self.assertNotIn("twitch.download_clip", actions)
        self.assertIn("twitch.clip_address", actions)


if __name__ == "__main__":
    unittest.main()
