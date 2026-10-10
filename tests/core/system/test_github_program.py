import hashlib
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

import httpx

from streamer_toolbox.core.system.github_program import GithubProgram

REPO = "someone/tool"
DOWNLOAD = f"https://github.com/{REPO}/releases/download"


def packed(**files: bytes) -> bytes:
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        for name, content in files.items():
            archive.writestr(name.replace("__", "/"), content)
    return data.getvalue()


class TestGithubProgram(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name) / "tools" / "tool"
        self.now = 1000.0
        self.asked: list[str] = []
        self.offline = False
        self.release("1.0", packed(**{"tool.exe": b"one", "LICENSE.txt": b"mit"}))

    def tearDown(self) -> None:
        self._dir.cleanup()

    def release(self, version: str, archive: bytes, digest: str | None = None, url: str = "") -> None:
        self.archive = archive
        self.listed = {"tag_name": version, "assets": [
            {"name": f"tool-{version}-Linux.zip", "browser_download_url": f"{DOWNLOAD}/{version}/linux.zip",
             "digest": "sha256:" + "0" * 64},
            {"name": f"tool-{version}-Windows.zip", "browser_download_url": url or f"{DOWNLOAD}/{version}/win.zip",
             "digest": digest if digest is not None else "sha256:" + hashlib.sha256(archive).hexdigest()}]}

    def _answer(self, request: httpx.Request) -> httpx.Response:
        self.asked.append(str(request.url))
        if self.offline:
            raise httpx.ConnectError("no internet")
        if request.url.host == "api.github.com":
            return httpx.Response(200, json=self.listed)
        return httpx.Response(200, content=self.archive)

    def program(self) -> GithubProgram:
        return GithubProgram(REPO, lambda name: name.endswith("-Windows.zip"), "tool.exe", self.folder,
                             httpx.MockTransport(self._answer), now=lambda: self.now)

    async def test_the_first_use_downloads_the_file_for_this_system_and_unpacks_it(self) -> None:
        program = self.program()
        self.assertEqual(program.version, "")
        file = await program.path()
        self.assertEqual((file, file.read_bytes()), (self.folder / "1.0" / "tool.exe", b"one"))
        self.assertEqual((self.folder / "1.0" / "LICENSE.txt").read_bytes(), b"mit")  # its notices come along
        self.assertEqual(self.asked, [f"https://api.github.com/repos/{REPO}/releases/latest",
                                      f"{DOWNLOAD}/1.0/win.zip"])
        self.assertEqual((program.version, list(self.folder.glob("*.zip"))), ("1.0", []))

    async def test_it_asks_again_only_after_a_day_and_takes_a_newer_one(self) -> None:
        await self.program().path()
        self.release("1.1", packed(**{"tool.exe": b"two"}))
        self.now += 3600
        self.assertEqual((await self.program().path()).read_bytes(), b"one")  # an hour later: GitHub isn't asked
        self.assertEqual(len(self.asked), 2)
        self.now += 24 * 3600
        file = await self.program().path()
        self.assertEqual((file.parent.name, file.read_bytes()), ("1.1", b"two"))
        self.assertFalse((self.folder / "1.0").exists())  # the old one is gone
        await self.program().path()
        self.assertEqual(len(self.asked), 4)  # the same day: not asked again

    async def test_a_check_that_fails_keeps_the_one_that_is_there(self) -> None:
        await self.program().path()
        self.now += 2 * 24 * 3600
        self.offline = True
        self.assertEqual((await self.program().path()).read_bytes(), b"one")
        before = len(self.asked)
        await self.program().path()
        self.assertEqual(len(self.asked), before)  # and it waits a day before it tries again
        with self.assertRaisesRegex(RuntimeError, "GitHub didn't answer"):
            await self.program().update()  # asked for by hand: the reason is told

    async def test_without_internet_and_without_the_program_it_says_so(self) -> None:
        self.offline = True
        with self.assertRaisesRegex(RuntimeError, "GitHub didn't answer for someone/tool"):
            await self.program().path()

    async def test_a_file_that_is_not_the_listed_one_is_never_used(self) -> None:
        cases = (({"digest": "sha256:" + "1" * 64}, "SHA-256 differs"), ({"digest": ""}, "lists no SHA-256"),
                 ({"url": "https://evil.test/win.zip"}, "is not a release of someone/tool"))
        for change, said in cases:
            self.release("1.0", self.archive, **change)
            with self.assertRaisesRegex(RuntimeError, said):
                await self.program().path()
            self.assertEqual([p.name for p in self.folder.glob("*")] if self.folder.exists() else [], [])
        self.release("1.0", packed(**{"other.exe": b"x"}))
        with self.assertRaisesRegex(RuntimeError, "has no tool.exe in it"):
            await self.program().path()
        self.listed["assets"] = self.listed["assets"][:1]
        with self.assertRaisesRegex(RuntimeError, "no file for this system"):
            await self.program().path()

    async def test_a_name_in_the_zip_cannot_lead_out_of_the_folder(self) -> None:
        self.release("1.0", packed(**{"..__..__evil.txt": b"x", "sub__tool.exe": b"one"}))
        file = await self.program().path()
        self.assertEqual(sorted(p.name for p in file.parent.iterdir()), ["evil.txt", "tool.exe"])
        self.assertFalse((self.folder.parent / "evil.txt").exists())

    async def test_update_says_whether_something_new_came(self) -> None:
        program = self.program()
        self.assertEqual(await program.update(), {"version": "1.0", "updated": True})
        self.assertEqual(await program.update(), {"version": "1.0", "updated": False})
        self.release("2.0", packed(**{"tool.exe": b"new"}))
        self.assertEqual(await program.update(), {"version": "2.0", "updated": True})


if __name__ == "__main__":
    unittest.main()
