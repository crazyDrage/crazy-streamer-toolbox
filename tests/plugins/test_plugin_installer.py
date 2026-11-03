import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import httpx

from streamer_toolbox.plugins.listed_plugin import ListedPlugin
from streamer_toolbox.plugins.plugin_installer import PluginInstaller


def plugin_zip(plugin_id: str, version: str, top: str = "") -> bytes:
    data = io.BytesIO()
    manifest = {"id": plugin_id, "name": plugin_id, "version": version, "api_version": 7}
    with zipfile.ZipFile(data, "w") as archive:
        archive.writestr(f"{top}plugin.json", json.dumps(manifest))
        archive.writestr(f"{top}main.py", f"# {version}")
    return data.getvalue()


class TestPluginInstaller(unittest.IsolatedAsyncioTestCase):
    """His answer of 2026-11-01: "the tool can download and import the plugin itself"."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        base = Path(self._dir.name)
        self.plugins, self.work = base / "plugins", base / "settings" / "cache" / "plugins"
        self.archive = plugin_zip("jokes", "1.0.0", top="jokes-main/")  # as GitHub's own zips have it

    def tearDown(self) -> None:
        self._dir.cleanup()

    def installer(self) -> PluginInstaller:
        return PluginInstaller(self.plugins, self.work,
                               httpx.MockTransport(lambda request: httpx.Response(200, content=self.archive)))

    @staticmethod
    def listed(version: str = "1.0.0", sha256: str = "") -> ListedPlugin:
        return ListedPlugin("jokes", "Jokes", version, "https://example.com/jokes.zip", sha256=sha256)

    @staticmethod
    def zip_bomb() -> bytes:
        """A small zip that unpacks to 201 MB of zeros."""
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("jokes/plugin.json", json.dumps({"id": "jokes", "version": "1.0.0"}))
            archive.writestr("jokes/zeros.bin", bytes(201 * 1024 * 1024))
        return data.getvalue()

    async def test_it_is_downloaded_into_the_plugins_folder(self) -> None:
        folder = await self.installer().install(self.listed(sha256=hashlib.sha256(self.archive).hexdigest()))
        self.assertEqual((folder, (folder / "main.py").read_text(encoding="utf-8")),
                         (self.plugins / "jokes", "# 1.0.0"))
        self.assertEqual(self.installer().installed(), {"jokes": "1.0.0"})
        self.assertEqual(list(self.work.glob("*.zip")), [])

    async def test_an_update_keeps_the_old_one(self) -> None:
        await self.installer().install(self.listed())
        self.archive = plugin_zip("jokes", "1.1.0")
        await self.installer().install(self.listed("1.1.0"))
        self.assertEqual(self.installer().installed(), {"jokes": "1.1.0"})
        self.assertEqual((self.work / "kept" / "jokes-1.0.0" / "main.py").read_text(encoding="utf-8"), "# 1.0.0")

    async def test_a_download_of_another_version_is_not_installed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "version 1.0.0, the listing says 1.1.0"):
            await self.installer().install(self.listed("1.1.0"))
        self.assertEqual(self.installer().installed(), {})

    async def test_remove_keeps_its_folder(self) -> None:
        await self.installer().install(self.listed())
        kept = self.installer().remove("jokes")
        self.assertEqual((self.installer().installed(), kept), ({}, self.work / "kept" / "jokes-1.0.0"))
        self.assertTrue((kept / "main.py").is_file())
        with self.assertRaisesRegex(RuntimeError, "no plugin folder"):
            self.installer().remove("jokes")

    async def test_a_wrong_file_is_not_installed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "SHA-256 differs"):
            await self.installer().install(self.listed(sha256="0" * 64))
        self.archive = plugin_zip("dice", "1.0.0")
        with self.assertRaisesRegex(RuntimeError, "plugin dice, not jokes"):
            await self.installer().install(self.listed())
        self.archive = self.zip_bomb()
        with self.assertRaisesRegex(RuntimeError, "more than 200 MB"):
            await self.installer().install(self.listed())
        self.archive = b"not a zip"
        with self.assertRaisesRegex(RuntimeError, "isn't a zip"):
            await self.installer().install(self.listed())
        self.assertFalse(self.plugins.exists())


if __name__ == "__main__":
    unittest.main()
