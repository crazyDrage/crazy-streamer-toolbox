import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import httpx

from streamer_toolbox.core.app_version import is_newer, stage, version_numbers
from streamer_toolbox.core.system.toolbox_update import READY, REPO, RESULT, ToolboxUpdate

DOWNLOAD = f"https://github.com/{REPO}/releases/download"
WINDOWS = "crazy-streamer-toolbox-windows.zip"


def packed(**files: bytes) -> bytes:
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return data.getvalue()


NEW = packed(**{"crazy-streamer-toolbox-windows/src/streamer_toolbox/__init__.py": b"",
                "crazy-streamer-toolbox-windows/python/python.exe": b"py"})


class TestToolboxUpdate(unittest.IsolatedAsyncioTestCase):
    """His next release plan, part 1: "both" (tell, and download and install)."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name) / "toolbox"
        (self.root / "python").mkdir(parents=True)
        self.folder = Path(self._dir.name) / "settings" / "cache" / "update"
        self.now = 1000.0
        self.asked: list[str] = []
        self.offline = False
        self.release("v0.3.0", NEW)
        self.all_releases = [{**self.listed, "tag_name": tag} for tag in ("v0.4.1-dev.1", "v0.4.0-beta.2",
                                                                           "v0.3.0", "v0.4.0-alpha.1")]

    def tearDown(self) -> None:
        self._dir.cleanup()

    def release(self, tag: str, archive: bytes, digest: str | None = None) -> None:
        self.archive = archive
        self.listed = {"tag_name": tag, "body": "## New\n- Events", "html_url": f"https://github.com/{REPO}/x",
                       "assets": [{"name": WINDOWS, "browser_download_url": f"{DOWNLOAD}/{tag}/{WINDOWS}",
                                   "digest": digest or "sha256:" + hashlib.sha256(archive).hexdigest()}]}

    def _answer(self, request: httpx.Request) -> httpx.Response:
        self.asked.append(str(request.url))
        if self.offline:
            raise httpx.ConnectError("no internet")
        if request.url.host == "api.github.com" and request.url.path.endswith("/latest"):
            return httpx.Response(200, json=self.listed)
        if request.url.host == "api.github.com":  # every release, the test versions too
            return httpx.Response(200, json=self.all_releases)
        return httpx.Response(200, content=self.archive)

    def update(self, channel: str = "release", version: str = "0.2.1") -> ToolboxUpdate:
        return ToolboxUpdate(self.root, self.folder, httpx.MockTransport(self._answer), now=lambda: self.now,
                             system="windows", version=version, settings=self.folder.parents[1], channel=channel)

    def test_versions(self) -> None:
        self.assertEqual(version_numbers("v0.10.2"), (0, 10, 2, 4, 0))
        self.assertTrue(is_newer("0.10.0", "0.9.9"))
        order = ["0.5.0-dev.1", "0.5.0-dev.2", "0.5.0-alpha.1", "0.5.0-beta.2", "0.5.0-beta.10", "0.5.0-rc.1",
                 "0.5.0", "0.5.1-dev.1"]
        self.assertEqual(sorted(reversed(order), key=version_numbers), order)
        self.assertEqual((stage("0.5.0-rc.1"), stage("0.5.0"), stage("0.5.0-gamma.1")), ("rc", "release", ""))
        self.assertFalse(is_newer("0.2.1", "0.2.1"))
        self.assertFalse(is_newer("nightly", "0.2.1"))

    async def test_a_newer_release_is_found_and_asked_for_at_most_once_an_hour(self) -> None:
        release = await self.update().check()
        self.assertEqual((release.version, release.asset, release.notes), ("0.3.0", WINDOWS, "## New\n- Events"))
        self.now += 1800
        self.assertEqual((await self.update().check()).version, "0.3.0")
        self.assertEqual(len(self.asked), 1)  # half an hour later: GitHub isn't asked
        self.now += 1800
        await self.update().check()
        self.assertEqual(len(self.asked), 2)  # an hour later it is (his round 88: a version of the same day)
        self.assertEqual(self.update().newest.version, "0.3.0")

    async def test_the_same_or_an_older_release_is_nothing(self) -> None:
        self.release("v0.2.1", NEW)
        self.assertIsNone(await self.update().check())
        self.offline = True
        with self.assertRaisesRegex(RuntimeError, "GitHub didn't answer"):
            await self.update().check(force=True)

    async def test_it_is_downloaded_checked_and_unpacked_for_the_swap(self) -> None:
        update = self.update()
        new = await update.prepare(await update.check())
        self.assertEqual(new, self.folder / "0.3.0" / "crazy-streamer-toolbox-windows")
        self.assertEqual((new / "python" / "python.exe").read_bytes(), b"py")
        self.assertEqual(json.loads((self.folder / READY).read_text(encoding="utf-8")),
                         {"version": "0.3.0", "new": str(new)})
        self.assertEqual(list(self.folder.glob("*.zip")), [])

    async def test_a_file_that_isnt_the_listed_one_is_not_used(self) -> None:
        self.release("v0.3.0", NEW, digest="sha256:" + "0" * 64)
        update = self.update()
        with self.assertRaisesRegex(RuntimeError, "SHA-256 differs"):
            await update.prepare(await update.check())
        self.assertFalse((self.folder / READY).exists())

    async def test_a_toolbox_run_from_its_code_only_tells(self) -> None:
        (self.root / ".git").mkdir()
        update = self.update()
        self.assertFalse(update.installable)
        with self.assertRaisesRegex(RuntimeError, "runs from its code"):
            await update.prepare(await update.check())

    async def test_the_swaps_result_is_read_once_and_leftovers_go(self) -> None:
        self.folder.mkdir(parents=True)
        (self.folder / RESULT).write_text(json.dumps({"version": "0.3.0", "ok": False, "error": "busy"}),
                                          encoding="utf-8")
        (self.folder / "old" / "src").mkdir(parents=True)
        update = self.update()
        self.assertEqual(update.result()["error"], "busy")
        self.assertIsNone(update.result())
        update.clean()
        self.assertFalse((self.folder / "old").exists())

    async def test_test_versions_only_when_he_chose_them(self) -> None:
        """His answers of 2026-11-01: normal versions by default; test versions "never in default"."""
        self.assertEqual((await self.update().check(force=True)).version, "0.3.0")
        self.assertEqual((await self.update("beta").check(force=True)).version, "0.4.0-beta.2")
        self.assertEqual((await self.update("dev").check(force=True)).version, "0.4.1-dev.1")
        self.assertIsNone(self.update().newest)  # back on releases only: the saved beta isn't offered

    async def test_a_test_version_on_releases_only_gets_the_release(self) -> None:
        self.release("v0.3.0", NEW)
        self.assertEqual((await self.update(version="0.3.0-rc.1").check(force=True)).version, "0.3.0")

    async def test_the_settings_are_copied_before_an_update(self) -> None:
        """His answer: "We have to make sure that we have a backup of the settings before we update"."""
        settings = self.folder.parents[1]
        (settings / "flows").mkdir(parents=True)
        (settings / "flows" / "thanks.toml").write_text("label = 'Thanks'", encoding="utf-8")
        update = self.update()
        await update.prepare(await update.check())
        backup = next((settings / "backups").glob("before-0.3.0-*.zip"))
        with zipfile.ZipFile(backup) as packed:
            names = packed.namelist()
        self.assertIn("flows/thanks.toml", names)
        self.assertFalse(any(n.startswith(("cache/", "backups/")) for n in names))


if __name__ == "__main__":
    unittest.main()
