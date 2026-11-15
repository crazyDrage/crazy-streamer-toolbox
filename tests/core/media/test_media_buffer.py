import json
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.media.media_buffer import MB, MediaBuffer
from tests.fakes.fake_media_web import PNG, FakeMediaWeb

PIC = "https://static-cdn.jtvnw.net/jtv_user_pictures/kit-profile_image-70x70.png"
CHAT = ("event_chat", "n3")


class TestMediaBuffer(unittest.IsolatedAsyncioTestCase):
    """His idea of 11-14: remember an address, keep the file on this PC, overlays load it from the toolbox. His
    11-15: the address is the box's own, the file is named <code>_<name>, latest.png is the newest."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name) / "cache" / "media"
        self.web = FakeMediaWeb()
        self.web.picture(PIC)
        self.now = 1000.0
        self.buffer = MediaBuffer(self.folder, self.web.transport, clock=lambda: self.now,
                                  resolve=self.web.resolve)

    def tearDown(self) -> None:
        self._dir.cleanup()

    async def test_a_picture_is_downloaded_once_and_served_from_its_folder(self) -> None:
        kept = await self.buffer.keep(PIC)
        self.assertEqual(PNG, kept.file.read_bytes())
        self.assertRegex(kept.address, r"^/toolbox/media/shared/media/[0-9a-f]{16}\.png$")
        self.assertEqual(kept, await self.buffer.keep(PIC))
        self.assertEqual([PIC], self.web.asked)
        self.assertEqual(kept.file, self.buffer.find_shared("media", kept.file.name))
        self.assertEqual(kept.file, self.buffer.find_shared("media", "latest.png"))

    async def test_a_box_in_a_flow_keeps_in_its_own_folder_at_its_own_address(self) -> None:
        kept = await self.buffer.keep(PIC, name="kit", box=CHAT)
        self.assertRegex(kept.address, r"^/toolbox/media/flows/box/event_chat/n3/[0-9a-f]{16}_kit\.png$")
        self.assertEqual(self.folder.resolve() / "flows" / "box" / "event_chat" / "n3", kept.file.parent)
        self.assertEqual(kept.file, self.buffer.find_for_box(*CHAT, kept.file.name))
        self.assertIsNone(self.buffer.find_for_box("event_chat", "n4", kept.file.name))
        self.assertIsNone(self.buffer.find_shared("media", kept.file.name))

    async def test_latest_is_the_newest_file_the_box_kept(self) -> None:
        other = "https://example.com/ann.gif"
        self.web.picture(other, kind="image/gif")
        first = await self.buffer.keep(PIC, box=CHAT)
        second = await self.buffer.keep(other, box=CHAT)
        self.assertEqual(second.file, self.buffer.find_for_box(*CHAT, "latest.png"))  # any ending: the newest
        self.assertEqual(second.file, self.buffer.find_for_box(*CHAT, "latest"))
        await self.buffer.keep(PIC, box=CHAT)  # kept before: no download, but it is the newest again
        self.assertEqual(first.file, self.buffer.find_for_box(*CHAT, "latest.gif"))
        self.assertEqual(2, len(self.web.asked))

    async def test_the_name_is_cleaned_and_the_same_address_keeps_its_file(self) -> None:
        kept = await self.buffer.keep(PIC, name="Kit Fox! ../x", box=CHAT)
        self.assertTrue(kept.file.name.endswith("_Kit-Fox-x.png"), kept.file.name)
        self.assertEqual(kept, await self.buffer.keep(PIC, name="other", box=CHAT))
        self.assertEqual(1, len(self.web.asked))

    async def test_boxes_with_a_folder_share_it_and_each_keeps_its_address(self) -> None:
        """His 11-15: "we may have the pfp on multiple flows, and then we share it"."""
        chat = await self.buffer.keep(PIC, folder="pfp", box=CHAT)
        raid = await self.buffer.keep(PIC, folder="pfp", box=("event_raid", "n2"))
        self.assertEqual(chat.file, raid.file)
        self.assertEqual(self.folder.resolve() / "shared" / "pfp", chat.file.parent)
        self.assertEqual([PIC], self.web.asked)
        self.assertIn("/flows/box/event_raid/n2/", raid.address)
        self.assertEqual(raid.file, self.buffer.find_for_box("event_raid", "n2", "latest.png"))
        self.assertEqual(chat.file, self.buffer.find_for_box(*CHAT, chat.file.name))
        await self.buffer.keep(PIC, box=CHAT)  # its Folder emptied again: back in its own
        self.assertEqual({"event_raid/n2": "pfp"}, json.loads((self.folder / "boxes.json").read_text("utf-8")))

    async def test_forget_drops_a_boxs_own_folder_and_leaves_shared_files(self) -> None:
        own = await self.buffer.keep(PIC, box=CHAT)
        shared = await self.buffer.keep(PIC, folder="pfp", box=("event_chat", "n5"))
        await self.buffer.keep(PIC, box=("event_chat", "n9"))
        self.buffer.forget("event_chat", ["n3", "n5"])
        self.assertFalse(own.file.parent.exists())
        self.assertTrue(shared.file.is_file())
        self.assertIsNone(self.buffer.find_for_box("event_chat", "n5", shared.file.name))  # no longer its box
        self.assertIsNotNone(self.buffer.find_for_box("event_chat", "n9", "latest"))
        self.buffer.forget("event_chat", ["n9"])
        self.assertFalse((self.folder / "flows" / "box" / "event_chat").exists())  # the empty flow folder too
        self.buffer.forget("..", [".."])  # nothing outside
        self.assertTrue(self.folder.is_dir())

    async def test_only_files_of_the_index_are_served(self) -> None:
        kept = await self.buffer.keep(PIC)
        (kept.file.parent / ("0" * 16 + ".png")).write_bytes(PNG)  # lies there, but was never kept
        self.assertIsNone(self.buffer.find_shared("media", "0" * 16 + ".png"))
        self.assertIsNone(self.buffer.find_shared("media", "index.json"))
        self.assertIsNone(self.buffer.find_shared("..", kept.file.name))
        self.assertIsNone(self.buffer.find_for_box("..", "n3", "latest"))
        self.assertIsNone(self.buffer.find_for_box("event_chat", "..", "latest"))
        self.assertIsNone(self.buffer.find_shared("other", "latest.png"))

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

    async def test_a_name_that_points_inside_is_refused(self) -> None:
        self.web.names.update({"localtest.me": ["127.0.0.1"], "nas.example.com": ["93.184.215.14", "192.168.1.5"],
                               "v6.example.com": ["fe80::1%12"]})
        for host in ("localtest.me", "nas.example.com", "v6.example.com"):
            self.web.picture(f"https://{host}/x.png")
            with self.assertRaisesRegex(ValueError, "this PC or the home network", msg=host):
                await self.buffer.keep(f"https://{host}/x.png")
        self.web.pages["https://example.com/away.png"] = (302, "text/plain", b"",
                                                          {"location": "https://localtest.me/x.png"})
        with self.assertRaisesRegex(ValueError, "home network"):
            await self.buffer.keep("https://example.com/away.png")
        self.assertEqual(["https://example.com/away.png"], self.web.asked)
        self.assertEqual([], list(self.folder.rglob("*.png")))

    async def test_a_name_that_cant_be_found_is_refused(self) -> None:
        async def nowhere(host: str) -> list[str]:
            raise OSError("no such name")

        buffer = MediaBuffer(self.folder, self.web.transport, resolve=nowhere)
        with self.assertRaisesRegex(ValueError, "can't be found"):
            await buffer.keep(PIC)
        self.assertEqual([], self.web.asked)

    async def test_a_full_folder_lets_the_longest_unused_go(self) -> None:
        urls = [f"https://example.com/{n}.png" for n in range(3)]
        for url in urls:
            self.web.picture(url, b"x" * (MB // 2))
        first = await self.buffer.keep(urls[0], max_mb=1.2, box=CHAT)
        self.now += 10
        second = await self.buffer.keep(urls[1], max_mb=1.2, box=CHAT)
        self.now += 10
        await self.buffer.keep(urls[0], max_mb=1.2, box=CHAT)  # used again: now the second is the longest unused
        self.now += 10
        await self.buffer.keep(urls[2], max_mb=1.2, box=CHAT)
        self.assertTrue(first.file.is_file())
        self.assertFalse(second.file.is_file())
        self.assertIsNone(self.buffer.find_for_box(*CHAT, second.file.name))

    async def test_a_file_is_downloaded_again_after_its_days(self) -> None:
        kept = await self.buffer.keep(PIC, days=1, box=CHAT)
        self.now += 2 * 24 * 60 * 60
        self.assertIsNone(self.buffer.find_for_box(*CHAT, kept.file.name))
        self.assertIsNone(self.buffer.find_for_box(*CHAT, "latest.png"))
        await self.buffer.keep(PIC, days=1, box=CHAT)
        self.assertEqual([PIC, PIC], self.web.asked)
        self.assertEqual(kept.file, self.buffer.find_for_box(*CHAT, kept.file.name))

    async def test_folder_names_are_checked(self) -> None:
        with self.assertRaisesRegex(ValueError, "folder name"):
            await self.buffer.keep(PIC, folder="../up")
        with self.assertRaisesRegex(ValueError, "no folder for the box"):
            await self.buffer.keep(PIC, box=("../x", "n3"))


if __name__ == "__main__":
    unittest.main()
