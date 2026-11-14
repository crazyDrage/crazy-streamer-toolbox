import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.media.media_actions import MediaActions
from streamer_toolbox.core.media.media_buffer import MediaBuffer
from tests.fakes.fake_media_web import FakeMediaWeb

PIC = "https://example.com/kit.png"


class TestKeepMediaLocally(unittest.IsolatedAsyncioTestCase):
    """The box: a web address in, where the toolbox keeps it out; a chat never stops at it."""

    async def asyncSetUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.web = FakeMediaWeb()
        self.web.picture(PIC)
        self.actions = ActionRegistry()
        MediaActions(MediaBuffer(Path(self._dir.name), self.web.transport)).add_to(self.actions)

    async def asyncTearDown(self) -> None:
        self._dir.cleanup()

    async def test_gives_the_toolbox_address_and_the_file(self) -> None:
        out = await self.actions.run("media.keep_locally", url=PIC)
        self.assertTrue(out["kept"])
        self.assertTrue(out["address"].startswith("/media/kept/media/"))
        self.assertTrue(Path(out["file"]).is_file())

    async def test_nothing_to_keep_gives_nothing(self) -> None:
        self.assertEqual({"address": "", "file": "", "kept": False},
                         await self.actions.run("media.keep_locally", url=" "))
        self.assertEqual([], self.web.asked)

    async def test_when_it_cant_be_kept_the_web_address_goes_on(self) -> None:
        with self.assertLogs("streamer_toolbox.core.media.boxes.keep_media_locally", "WARNING"):
            out = await self.actions.run("media.keep_locally", url="https://example.com/gone.png")
        self.assertEqual({"address": "https://example.com/gone.png", "file": "", "kept": False}, out)


if __name__ == "__main__":
    unittest.main()
