import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.media.media_buffer import MB, MediaBuffer
from tests.fakes.fake_media_web import PNG, FakeMediaWeb

PIC = "https://static-cdn.jtvnw.net/jtv_user_pictures/kit-profile_image-70x70.png"


class TestMediaBuffer(unittest.IsolatedAsyncioTestCase):
    """His idea of 11-14: remember an address, keep the file on this PC, overlays load it from the toolbox."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name) / "cache" / "media"
        self.web = FakeMediaWeb()
        self.web.picture(PIC)
        self.now = 1000.0
        self.buffer = MediaBuffer(self.folder, self.web.transport, clock=lambda: self.now)

    def tearDown(self) -> None:
        self._dir.cleanup()

    async def test_a_picture_is_downloaded_once_and_served_from_its_folder(self) -> None:
        kept = await self.buffer.keep(PIC)
        self.assertEqual(PNG, kept.file.read_bytes())
        self.assertTrue(kept.address.startswith("/media/kept/media/") and kept.address.endswith(".png"))
        self.assertEqual(kept, await self.buffer.keep(PIC))
        self.assertEqual([PIC], self.web.asked)
        self.assertEqual(kept.file, self.buffer.find("media", kept.file.name))

    async def test_only_files_of_the_index_are_served(self) -> None:
        kept = await self.buffer.keep(PIC)
        (kept.file.parent / ("0" * 32 + ".png")).write_bytes(PNG)  # lies there, but was never kept
        self.assertIsNone(self.buffer.find("media", "0" * 32 + ".png"))
        self.assertIsNone(self.buffer.find("media", "index.json"))
        self.assertIsNone(self.buffer.find("..", kept.file.name))

    async def test_what_isnt_a_picture_or_video_is_refused(self) -> None:
        self.web.pages["https://example.com/page"] = (200, "text/html", b"<script>", {})
        self.web.pages["https://example.com/logo.svg"] = (200, "image/svg+xml", b"<svg/>", {})
        for url in ("https://example.com/page", "https://example.com/logo.svg"):
            with self.assertRaisesRegex(ValueError, "not a picture or video"):
                await self.buffer.keep(url)
        with self.assertRaisesRegex(ValueError, "answered 404"):
            await self.buffer.keep("https://example.com/gone.png")

    async def test_a_file_too_big_is_refused(self) -> None:
        self.web.picture("https://example.com/big.png", b"x" * (MB + 1))
        with self.assertRaisesRegex(ValueError, "bigger than 1 MB"):
            await self.buffer.keep("https://example.com/big.png", file_mb=1)
        self.assertEqual([], list(self.folder.rglob("*.png")))

    async def test_this_pc_and_the_home_network_are_never_asked(self) -> None:
        for url in ("http://127.0.0.1:8850/x.png", "http://192.168.1.1/admin.png", "http://localhost/x.png",
                    "http://router/x.png", "http://box.local/x.png", "file:///C:/x.png", "C:/x.png", ""):
            with self.assertRaises(ValueError, msg=url):
                await self.buffer.keep(url)
        self.web.pages["https://example.com/away.png"] = (302, "text/plain", b"",
                                                          {"location": "http://10.0.0.1/x.png"})
        with self.assertRaisesRegex(ValueError, "home network"):
            await self.buffer.keep("https://example.com/away.png")
        self.assertEqual(["https://example.com/away.png"], self.web.asked)

    async def test_a_full_folder_lets_the_longest_unused_go(self) -> None:
        urls = [f"https://example.com/{n}.png" for n in range(3)]
        for url in urls:
            self.web.picture(url, b"x" * (MB // 2))
        first = await self.buffer.keep(urls[0], max_mb=1.2)
        self.now += 10
        second = await self.buffer.keep(urls[1], max_mb=1.2)
        self.now += 10
        await self.buffer.keep(urls[0], max_mb=1.2)  # used again: now the second is the longest unused
        self.now += 10
        await self.buffer.keep(urls[2], max_mb=1.2)
        self.assertTrue(first.file.is_file())
        self.assertFalse(second.file.is_file())
        self.assertIsNone(self.buffer.find("media", second.file.name))

    async def test_a_file_is_downloaded_again_after_its_days(self) -> None:
        kept = await self.buffer.keep(PIC, days=1)
        self.now += 2 * 24 * 60 * 60
        self.assertIsNone(self.buffer.find("media", kept.file.name))
        await self.buffer.keep(PIC, days=1)
        self.assertEqual([PIC, PIC], self.web.asked)
        self.assertEqual(kept.file, self.buffer.find("media", kept.file.name))

    async def test_folders_are_apart_and_their_names_are_checked(self) -> None:
        kept = await self.buffer.keep(PIC, folder="chat_pictures")
        self.assertEqual(self.folder.resolve() / "chat_pictures" / kept.file.name, kept.file)
        self.assertIsNone(self.buffer.find("media", kept.file.name))
        with self.assertRaisesRegex(ValueError, "folder name"):
            await self.buffer.keep(PIC, folder="../up")


if __name__ == "__main__":
    unittest.main()
